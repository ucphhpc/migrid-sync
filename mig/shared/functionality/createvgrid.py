#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# createvgrid - [insert a few words of module description on this line]
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

"""Create a new VGrid"""

import os
import shutil
import subprocess

import shared.returnvalues as returnvalues
from shared.fileio import write_file, pickle, make_symlink
from shared.functional import validate_input_and_cert, REJECT_UNSET
from shared.init import initialize_main_variables
from shared.useradm import client_id_dir
from shared.validstring import valid_dir_input
from shared.vgrid import vgrid_is_owner


def signature():
    """Signature of the main function"""

    defaults = {'vgrid_name': REJECT_UNSET}
    return ['text', defaults]


def create_wiki(
    configuration,
    vgrid_name,
    wiki_dir,
    output_objects,
    ):
    """Create new Moin Moin wiki"""

    cgi_template_script = os.path.join(configuration.moin_share,
            'server', 'moin.cgi')
    cgi_template_wikiconf = os.path.join(configuration.moin_share,
            'config', 'wikiconfig.py')

    # Depending on the MoinMoin installation some of the
    # configuration strings may vary slightly

    cgi_template_etc = configuration.moin_etc
    cgi_template_etc_alternative = '/path/to/wikiconfig'
    cgi_template_name = 'Untitled Wiki'
    cgi_template_data_str = './data/'
    cgi_template_data_str_alternative = '../data/'
    cgi_template_underlay_str = './underlay/'
    cgi_template_underlay_str_alternative = '../underlay/'
    cgi_template_data = os.path.join(configuration.moin_share, 'data')
    cgi_template_underlay = os.path.join(configuration.moin_share,
            'underlay')

    cgi_wiki_bin = os.path.join(wiki_dir, 'cgi-bin')
    cgi_wiki_etc = os.path.join(wiki_dir, 'etc')
    cgi_wiki_name = vgrid_name
    cgi_wiki_data = os.path.join(wiki_dir, 'data')
    cgi_wiki_underlay = os.path.join(wiki_dir, 'underlay')
    cgi_wiki_script = os.path.join(cgi_wiki_bin, 'moin.cgi')
    cgi_wiki_wikiconf = os.path.join(cgi_wiki_etc, 'wikiconfig.py')
    try:

        # Create wiki directory

        os.mkdir(wiki_dir)
        os.mkdir(cgi_wiki_bin)
        os.mkdir(cgi_wiki_etc)

        # Create modified MoinMoin cgi script that uses local rather than global config
        # In this way modification to one vgrid wiki will not affect other vgrid wikis.

        template_fd = open(cgi_template_script, 'r')
        template_script = template_fd.readlines()
        template_fd.close()
        cgi_script = []

        # Simply replace all occurences of template conf dir with vgrid wiki conf dir.
        # In that way config files (python modules) are automatically loaded from there.

        # IMPORTANT NOTE:
        # prevent users writing in cgi-bin and etc dir to avoid remote execution exploit

        for line in template_script:
            line = line.replace(cgi_template_etc_alternative,
                                cgi_wiki_etc)
            line = line.replace(cgi_template_etc, cgi_wiki_etc)
            cgi_script.append(line)
        cgi_fd = open(cgi_wiki_script, 'w')
        cgi_fd.writelines(cgi_script)
        cgi_fd.close()
        os.chmod(cgi_wiki_script, 0555)
        os.chmod(cgi_wiki_bin, 0555)

        # Now create the vgrid specific wiki configuration file

        template_fd = open(cgi_template_wikiconf, 'r')
        template_wikiconfig = template_fd.readlines()
        template_fd.close()
        cgi_wikiconfig = []
        for line in template_wikiconfig:

            # Simply replace the wiki name, data dir and underlay dir.
            # Remaining options can be modified by owners if needed

            line = line.replace(cgi_template_name, cgi_wiki_name)
            line = line.replace(cgi_template_data_str_alternative,
                                cgi_wiki_data)
            line = line.replace(cgi_template_data_str, cgi_wiki_data)
            line = line.replace(cgi_template_underlay_str_alternative,
                                cgi_wiki_underlay)
            line = line.replace(cgi_template_underlay_str,
                                cgi_wiki_underlay)
            cgi_wikiconfig.append(line)
        cgi_fd = open(cgi_wiki_wikiconf, 'w')
        cgi_fd.writelines(cgi_wikiconfig)
        cgi_fd.close()
        os.chmod(cgi_wiki_wikiconf, 0444)
        os.chmod(cgi_wiki_etc, 0555)

        # Copy example data and underlay directories directly

        shutil.copytree(cgi_template_data, cgi_wiki_data)
        shutil.copytree(cgi_template_underlay, cgi_wiki_underlay)
        os.chmod(wiki_dir, 0555)
        return True
    except Exception, exc:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not create vgrid wiki: %s'
                               % exc})
        return False


def create_scm(
    configuration,
    vgrid_name,
    scm_dir,
    output_objects,
    ):
    """Create new Mercurial SCM repository"""

    kind = 'member'
    scm_alias = 'vgridscm'
    server_url = configuration.migserver_https_cert_url
    server_url_without_port = ':'.join(server_url.split(':')[:2])
    if scm_dir.find('private') > -1:
        kind = 'owner'
        scm_alias = 'vgridownerscm'
        server_url = configuration.migserver_https_cert_url
    elif scm_dir.find('public') > -1:
        kind = 'public'
        scm_alias = 'vgridpublicscm'
        server_url = configuration.migserver_http_url
    cgi_template_script = os.path.abspath(configuration.hgweb_path)

    # Depending on the Mercurial installation some of the
    # configuration strings may vary slightly

    cgi_template_name = 'repository name'
    cgi_template_repo = '/path/to/repo'
    cgi_scm_name = '%s %s SCM repository' % (vgrid_name, kind)
    repo_base = 'repo'
    cgi_scm_repo = os.path.join(scm_dir, repo_base)
    repo_rc = os.path.join(cgi_scm_repo, '.hg', 'hgrc')
    repo_readme = os.path.join(cgi_scm_repo, 'readme')
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

For full access the repository you need a Mercurial client.
Once again for non-public repositories you need client certificate support
in the client. Mercurial 1.3 and later is known to work with certificates,
but please refer to the documentation provided with your installation if you
have an older version. Installation of a newer version in user space should
be possible if case you do not have administrator privileges.

On the client a ~/.hgrc with something like:
[auth]
migserver.prefix = %(server_url_without_port)s
migserver.key = /path/to/mig/key.pem
migserver.cert = /path/to/mig/cert.pem

[web]
cacerts = /path/to/mig/cacert.pem

should allow access with your certificate.
In the above /path/to/mig is typically /home/USER/.mig where USER is
replaced by your login.

You can check out your own copy of the repository with:
hg clone %(server_url)s/%(scm_alias)s/%(vgrid_name)s [DESTINATION]

Please refer to the Mercurial documentation for further information about
the commands and work flows of this distributed SCM.
''' % {'vgrid_name': vgrid_name, 'kind': kind, 'scm_alias': scm_alias,
       'server_url': server_url,
       'server_url_without_port': server_url_without_port}

    cgi_scm_bin = os.path.join(scm_dir, 'cgi-bin')
    cgi_scm_script = os.path.join(cgi_scm_bin, 'hgweb.cgi')
    try:

        # Create scm directory

        os.mkdir(scm_dir)
        os.mkdir(cgi_scm_bin)
        os.mkdir(cgi_scm_repo)

        # Create modified Mercurial cgi script that uses local scm repo.
        # In this way modification to one vgrid scm will not affect others.

        template_fd = open(cgi_template_script, 'r')
        template_script = template_fd.readlines()
        template_fd.close()
        cgi_script = []

        # IMPORTANT NOTE:
        # prevent users writing in cgi-bin dir to avoid remote execution exploit

        for line in template_script:
            line = line.replace(cgi_template_name,
                                cgi_scm_name)
            line = line.replace(cgi_template_repo, cgi_scm_repo)
            cgi_script.append(line)
        cgi_fd = open(cgi_scm_script, 'w')
        cgi_fd.writelines(cgi_script)
        cgi_fd.close()
        os.chmod(cgi_scm_script, 0555)
        os.chmod(cgi_scm_bin, 0555)
        os.chmod(cgi_scm_repo, 0755)
        readme_fd = open(repo_readme, 'w')
        readme_fd.write(readme_text)
        readme_fd.close()
        subprocess.call([configuration.hg_path, 'init', cgi_scm_repo])
        subprocess.call([configuration.hg_path, 'add', repo_readme])
        subprocess.call([configuration.hg_path, 'commit', '-m"init"', repo_readme])
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
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not create vgrid scm: %s'
                               % exc})
        return False


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id)
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
    vgrid_name = accepted['vgrid_name'][-1]

    # No owner check here so we need to specifically check for illegal
    # directory traversals

    if not valid_dir_input(configuration.vgrid_home, vgrid_name):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Illegal vgrid_name: %s' % vgrid_name})
        logger.warning("createvgrid registered possible illegal directory traversal attempt by '%s': vgrid name '%s'"
                        % (client_id, vgrid_name))
        return (output_objects, returnvalues.CLIENT_ERROR)

    # Please note that base_dir must end in slash to avoid access to other
    # user dirs when own name is a prefix of another user name

    base_dir = os.path.abspath(os.path.join(configuration.vgrid_home,
                               vgrid_name)) + os.sep
    public_base_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_public_base,
                        vgrid_name)) + os.sep
    public_wiki_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_public_base,
                        vgrid_name, '.vgridwiki')) + os.sep
    public_scm_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_public_base,
                        vgrid_name, '.vgridscm')) + os.sep
    private_base_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                        vgrid_name)) + os.sep
    private_wiki_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                        vgrid_name, '.vgridwiki')) + os.sep
    private_scm_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_private_base,
                        vgrid_name, '.vgridscm')) + os.sep
    vgrid_files_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_files_home,
                        vgrid_name)) + os.sep
    vgrid_wiki_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_files_home,
                        vgrid_name, '.vgridwiki')) + os.sep
    vgrid_scm_dir = \
        os.path.abspath(os.path.join(configuration.vgrid_files_home,
                        vgrid_name, '.vgridscm')) + os.sep

    # does vgrid exist?

    if os.path.isdir(base_dir):
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'vgrid %s cannot be created because it already exists!'
                               % vgrid_name})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # verify that client is owner of imada or imada/topology if trying to
    # create imada/topology/test

    vgrid_name_list = vgrid_name.split('/')
    vgrid_name_list_length = len(vgrid_name_list)
    if vgrid_name_list_length <= 0:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'vgrid_name not specified?'})
        return (output_objects, returnvalues.SYSTEM_ERROR)
    elif vgrid_name_list_length == 1:

        # anyone can create base vgrid

        new_base_vgrid = True
    else:
        new_base_vgrid = False
        vgrid_name_without_last_fragment = \
            '/'.join(vgrid_name_list[0:vgrid_name_list_length - 1])
        if not vgrid_is_owner(vgrid_name_without_last_fragment,
                              client_id, configuration):
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'You must be an owner of a parent vgrid to create a sub vgrid'
                                  })
            return (output_objects, returnvalues.CLIENT_ERROR)

    # make sure all dirs can be created (that a file or directory with the same name
    # do not exist prior to the vgrid creation)

    try_again_string = \
        'vgrid cannot be created, a file or directory exists with the same name, please try again with a new name!'
    if os.path.exists(public_base_dir):
        output_objects.append({'object_type': 'error_text', 'text'
                              : try_again_string})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if os.path.exists(private_base_dir):
        output_objects.append({'object_type': 'error_text', 'text'
                              : try_again_string})
        return (output_objects, returnvalues.CLIENT_ERROR)

    if os.path.exists(vgrid_files_dir):
        output_objects.append({'object_type': 'error_text', 'text'
                              : try_again_string})
        return (output_objects, returnvalues.CLIENT_ERROR)

    # create directory to store vgrid files

    try:
        os.mkdir(base_dir)
    except Exception, exc:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not create vgrid directory, remember to create parent vgrid before creating a sub-vgrid.'
                              })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # create directory to store vgrid public_base files

    try:
        os.mkdir(public_base_dir)
        pub_readme = os.path.join(public_base_dir, 'README')
        if not os.path.exists(pub_readme):
            write_file("""= Public Web Page =
This directory is used for hosting the public web page for the %s VGrid.
It is accessible by the public from the VGrids page or directly using the URL
%s/vgrid/%s/

Just update the index.html file to suit your wishes for an entry page. It can
link to any other material in this folder or subfolders with relative
addresses. So it is possible to create a full web site with multiple pages and
rich content like on other web hosting services. However, there's no support
for server side scripting with Python, ASP or PHP for security reasons.
""" % (vgrid_name, configuration.migserver_http_url, vgrid_name),
                       pub_readme, logger)
        pub_entry_page = os.path.join(public_base_dir, 'index.html')
        if not os.path.exists(pub_entry_page):
            write_file("<!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'>\n<html><head><title>Public entry page not created yet..</title></head><body>No public entrypage created yet! (If you are owner of the vgrid, overwrite public_base/%s/index.html to place it here)</body></html>"
                        % vgrid_name, pub_entry_page, logger)
    except Exception, exc:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not create vgrid public_base directory, remember to create parent vgrid before creating a sub-vgrid.'
                              })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # create directory to store vgrid private_base files

    try:
        os.mkdir(private_base_dir)
        priv_readme = os.path.join(private_base_dir, 'README')
        if not os.path.exists(priv_readme):
            write_file("""= Private Web Page =
This directory is used for hosting the private web page for the %s VGrid.
It is only accessible for members and owners either from the VGrids page or
directly using the URL
%s/vgrid/%s/path/index.html

Just update the index.html file to suit your wishes for an entry page. It can
link to any other material in this folder or subfolders with relative
addresses. So it is possible to create a full web site with multiple pages and
rich content like on other web hosting services. However, there's no support
for server side scripting with Python, ASP or PHP for security reasons.
""" % (vgrid_name, configuration.migserver_https_cert_url, vgrid_name),
                       priv_readme, logger)
        priv_entry_page = os.path.join(private_base_dir, 'index.html')
        if not os.path.exists(priv_entry_page):
            write_file("<!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'>\n<html><head><title>Private entry page not created yet..</title></head><body>No private entrypage created yet! (If you are owner of the vgrid, overwrite private_base/%s/index.html to place it here)<br>  <p><a href='http://validator.w3.org/check?uri=referer'><img src='http://www.w3.org/Icons/valid-html401' alt='Valid HTML 4.01 Transitional' height='31' width='88' /></a> </p></body></html>"
                        % vgrid_name, priv_entry_page, logger)
    except Exception, exc:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not create vgrid private_base directory, remember to create parent vgrid before creating a sub-vgrid.'
                              })
        return (output_objects, returnvalues.CLIENT_ERROR)

    # create directory in vgrid_files_home to contain internal files for the vgrid

    try:
        os.mkdir(vgrid_files_dir)
        share_readme = os.path.join(vgrid_files_dir, 'README')
        if not os.path.exists(share_readme):
            write_file("""= Private Share =
This directory is used for hosting private files for the %s VGrid.
It is accessible for all members and owners as a virtual %s directory in the
user home directory. Therefore it is also usable as source and destination
for job input and output.
""" % (vgrid_name, vgrid_name), share_readme, logger)
    except Exception, exc:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not create vgrid files directory.'
                              })
        logger.error('Could not create vgrid files directory.',
                     str(exc))
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if configuration.moin_share and configuration.moin_etc:

        # create public, member, owner wiki's in the vgrid dirs

        for wiki_dir in [public_wiki_dir, private_wiki_dir,
                         vgrid_wiki_dir]:
            if not create_wiki(configuration, vgrid_name, wiki_dir,
                               output_objects):
                return (output_objects, returnvalues.SYSTEM_ERROR)

    if configuration.hg_path and configuration.hgweb_path:

        # create participant scm repo in the vgrid shared dir

        for scm_dir in [public_scm_dir, private_scm_dir, vgrid_scm_dir]:
            if not create_scm(configuration, vgrid_name, scm_dir,
                               output_objects):
                return (output_objects, returnvalues.SYSTEM_ERROR)

    # create pickled owners list with client_id as owner
    # only add user in owners list if new vgrid is a base vgrid (because symlinks to
    # subdirs are not necessary, and an owner is per definition owner of sub vgrids).

    owner_file = os.path.join(base_dir, 'owners')
    owner_list = []
    if new_base_vgrid == True:
        owner_list.append(client_id)
    else:
        owner_list.append('')

    status = pickle(owner_list, owner_file, logger)
    if not status:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not save new list of owners'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # create empty pickled members list

    member_file = os.path.join(base_dir, 'members')
    status2 = pickle([], member_file, logger)
    if not status2:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not pickle and save list'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    # create empty pickled resources list

    resources_file = os.path.join(base_dir, 'resources')
    status3 = pickle([], resources_file, logger)
    if not status3:
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Could not pickle and save list'})
        return (output_objects, returnvalues.SYSTEM_ERROR)

    if new_base_vgrid:

        # create sym link from creators (client_id) home directory to directory containing the vgrid files

        src = vgrid_files_dir
        dst = os.path.join(configuration.user_home, client_dir,
                           vgrid_name)
        if not make_symlink(src, dst, logger):
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Could not create link to vgrid files!'
                                  })
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # make sure public_base dir exists in users home dir

        user_public_base = os.path.join(configuration.user_home,
                client_dir, 'public_base')
        try:
            os.mkdir(user_public_base)
        except:

            # o.out("could not create dir %s. Probably because it already exists." % user_public_base)

            pass

        public_base_dst = os.path.join(user_public_base, vgrid_name)

        # create sym link for public_base

        if not make_symlink(public_base_dir, public_base_dst, logger):
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

            # o.out("could not create dir %s. Probably because it already exists." % user_private_base)

            pass

        private_base_dst = os.path.join(user_private_base, vgrid_name)

        # create sym link for private_base

        if not make_symlink(private_base_dir, private_base_dst, logger):
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Could not create link to private_base dir!'
                                  })
            return (output_objects, returnvalues.SYSTEM_ERROR)

        # create sym link to make private_base available by linking it to wwwuser/vgrid

        # ******** code below removed because apache rewriterule now sends requests for
        # https://.../vgrid/vgrid_name to a python script that validates the client!

        # try:
            # make sure root dir exists
            # os.mkdir(os.path.join(configuration.user_home, "vgrid"))
            # except:
                # dir probably exists
                # pass

                # if not make_symlink(private_base_dir, os.path.join(configuration.user_home, "vgrid", vgrid_name), logger):
                    # o.out("Could not create link in wwwuser/vgrid/%s" % vgrid_name)
                    # o.reply_and_exit(o.ERROR)

        # create sym link to make public_base public by linking it to wwwpublic/vgrid

        try:

            # make sure root dir exists

            os.mkdir(os.path.join(configuration.wwwpublic, 'vgrid'))
        except:

            # dir probably exists

            pass

        if not make_symlink(public_base_dir,
                            os.path.join(configuration.wwwpublic,
                            'vgrid', vgrid_name), logger):
            output_objects.append({'object_type': 'error_text', 'text'
                                  : 'Could not create link in wwwpublic/vgrid/%s'
                                   % vgrid_name})
            return (output_objects, returnvalues.SYSTEM_ERROR)

    output_objects.append({'object_type': 'text', 'text'
                          : 'vgrid %s created!' % vgrid_name})
    output_objects.append({'object_type': 'link',
                           'destination': 'adminvgrid.py?vgrid_name=%s' % vgrid_name,
                           'class': 'adminlink',
                           'title': 'Administrate your new VGrid',
                           'text': 'Administration for %s' % vgrid_name})
    return (output_objects, returnvalues.OK)


