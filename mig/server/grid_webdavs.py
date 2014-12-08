#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# grid_webdavs - secure WebDAV server providing access to MiG user homes
# Copyright (C) 2003-2014  The MiG Project lead by Brian Vinter
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

"""Provide secure WebDAV access to MiG user homes using wsgidav"""

import logging
import os
import sys
import time
import urlparse

try:
    from wsgidav.wsgidav_app import DEFAULT_CONFIG, WsgiDAVApp
    from wsgidav.server import ext_wsgiutils_server
    from wsgidav.fs_dav_provider import FileResource, FolderResource, \
         FilesystemProvider
except ImportError:
    print "ERROR: the python wsgidav module is required for this daemon"
    sys.exit(1)

from wsgiref.simple_server import make_server
        
from shared.base import invisible_path, force_unicode
from shared.conf import get_configuration_object
from shared.griddaemons import get_fs_path, strip_root, \
     acceptable_chmod, refresh_users, hit_rate_limit, update_rate_limit, \
     expire_rate_limit
from shared.useradm import check_password_hash


configuration, logger = None, None



class MiGFileResource(FileResource):
    """Hide invisible files from all access"""
    def __init__(self, path, environ, filePath):
        super(MiGFileResource, self).__init__(path, environ, filePath)
        if invisible_path(path):
            raise DAVError(HTTP_FORBIDDEN)

    # TODO: override access on more methods?


class MiGFolderResource(FolderResource):
    """Hide invisible files from all access"""
    def __init__(self, path, environ, filePath):
        super(MiGFolderResource, self).__init__(path, environ, filePath)
        if invisible_path(path):
            raise DAVError(HTTP_FORBIDDEN)

    # TODO: override access on more methods?
    
    def getMemberNames(self):
        """Return list of direct collection member names (utf-8 encoded).
        
        See DAVCollection.getMemberNames()
        """
        return [i for i in super(MiGFolderResource, self).getMemberNames() if \
                not invisible_path(i)]


class MiGFilesystemProvider(FilesystemProvider):
    """
    Overrides the default FilesystemProvider to include chroot support and
    hidden files like in other MiG file interfaces.
    """

    def __init__(self, directory, server_conf, dav_conf):
        """Simply call parent constructor"""
        super(MiGFilesystemProvider, self).__init__(directory)
        
        self.daemon_conf = server_conf.daemon_conf
        self.chroot_exceptions = self.daemon_conf['chroot_exceptions']
        self.chmod_exceptions = self.daemon_conf['chmod_exceptions']

    # Use shared daemon fs helper functions
    
    def _get_fs_path(self, davs_path):
        """Wrap helper"""
        #logger.debug("get_fs_path: %s" % davs_path)
        reply = get_fs_path(davs_path, self.rootFolderPath,
                            self.chroot_exceptions)
        logger.debug("get_fs_path returns: %s :: %s" % (davs_path, reply))
        return reply

    def _strip_root(self, davs_path):
        """Wrap helper"""
        #logger.debug("strip_root: %s" % davs_path)
        reply = strip_root(davs_path, self.root, self.chroot_exceptions)
        logger.debug("strip_root returns: %s :: %s" % (davs_path, reply))
        return reply
    
    def _acceptable_chmod(self, davs_path, mode):
        """Wrap helper"""
        #logger.debug("acceptable_chmod: %s" % davs_path)
        reply = acceptable_chmod(davs_path, mode, self.chmod_exceptions)
        logger.debug("acceptable_chmod returns: %s :: %s" % (davs_path, reply))
        return reply

    def _locToFilePath(self, path):
        """Convert resource path to a unicode absolute file path with MiG file
        system restrictions.
        """
        assert self.rootFolderPath is not None
        pathInfoParts = path.strip("/").split("/")
        real_path = os.path.abspath(os.path.join(self.rootFolderPath,
                                                 # TODO: insert user home here!
                                                 #self.user_home,
                                                 *pathInfoParts))
        
        try:
            filename = self._get_fs_path(real_path)
        except ValueError, vae:
            logger.warning("illegal path requested: %s :: %s" % (real_path,
                                                                 vae))
            raise RuntimeError("Security exception: tried illegal access: %s" \
                               % path)
        real_path = force_unicode(real_path)
        return real_path
    
    def getResourceInst(self, path, environ):
        """Return info dictionary for path.

        See DAVProvider.getResourceInst()

        Override to filter MiG invisible paths from content.
        """
        self._count_getResourceInst += 1
        real_path = self._locToFilePath(path)
        if not os.path.exists(real_path):
            return None
        
        if os.path.isdir(real_path):
            return MiGFolderResource(path, environ, real_path)
        return MiGFileResource(path, environ, real_path)
                                                            
                        

def update_users(configuration, user_map):
    """Update dict with username password pairs"""
    refresh_users(configuration, 'davs')
    domain_map = user_map.get('/', {})
    # TODO: makecustom domaincontroller to support pw hashes instead of raw pw
    for user_obj in configuration.daemon_conf['users']:
        if not domain_map.has_key(user_obj.username):
            domain_map[user_obj.username] = {'password': user_obj.password}
    # TMP!!
    domain_map['test'] = {'password': 'tester'}
    user_map['/'] = domain_map

def run(configuration):
    """SSL wrapped HTTP server for secure WebDAV access"""

    dav_conf = configuration.daemon_conf
    config = DEFAULT_CONFIG.copy()
    config.update(dav_conf)
    # TMP! should look up users on demand
    user_map = {}
    update_users(configuration, user_map)
    ## TMP! until we get chrooting
    #from tempfile import gettempdir
    #dav_conf['root_dir'] = gettempdir()
    config.update({
        "provider_mapping": {"/": MiGFilesystemProvider(dav_conf['root_dir'],
                                                        configuration,
                                                        dav_conf)},
        "user_mapping": user_map,
        "enable_loggers": [],
        "propsmanager": True,      # True: use property_manager.PropertyManager
        "locksmanager": True,      # True: use lock_manager.LockManager
        "domaincontroller": None,  # None: domain_controller.WsgiDAVDomainController(user_mapping)
        })
    print('User list: %s' % config['user_mapping'])
    app = WsgiDAVApp(config)

    runner = make_server(config["host"], config["port"], app)
    ## Or we could use the default server that is part of the WsgiDAV package:
    #ext_wsgiutils_server.serve(config, app)

    print('Listening on %(host)s (%(port)s)' % config)

    min_expire_delay = 300
    last_expire = time.time()
    try:
        while True:
            runner.handle_request()
            if last_expire + min_expire_delay < time.time():
                last_expire = time.time()
                expired = expire_rate_limit(configuration, "davs")
                logger.debug("Expired rate limit entries: %s" % expired)
    except KeyboardInterrupt:
        # forward KeyboardInterrupt to main thread
        raise


if __name__ == "__main__":
    configuration = get_configuration_object()
    nossl = False

    # Use separate logger
    logging.basicConfig(filename=configuration.user_davs_log,
                        level=logging.DEBUG,
                        format="%(asctime)s %(levelname)s %(message)s")
    logger = logging

    # Allow configuration overrides on command line
    if sys.argv[1:]:
        nossl = bool(sys.argv[1])
    if sys.argv[2:]:
        configuration.user_davs_address = sys.argv[2]
    if sys.argv[3:]:
        configuration.user_davs_port = int(sys.argv[3])

    configuration.dav_cfg = {
        'nossl': nossl,
        'verbose': 1,
        }

    if not configuration.site_enable_davs:
        err_msg = "WebDAVS access to user homes is disabled in configuration!"
        logger.error(err_msg)
        print err_msg
        sys.exit(1)

    if not nossl:
        # TODO: switch to Cherrypy.wsgiserver to include ssl support
        configuration.dav_cfg['ssl_certificate'] = configuration.user_davs_key
        configuration.dav_cfg['ssl_private_key'] = configuration.user_davs_key

    chroot_exceptions = [os.path.abspath(configuration.vgrid_private_base),
                         os.path.abspath(configuration.vgrid_public_base),
                         os.path.abspath(configuration.vgrid_files_home),
                         os.path.abspath(configuration.resource_home)]
    # Don't allow chmod in dirs with CGI access as it introduces arbitrary
    # code execution vulnerabilities
    chmod_exceptions = [os.path.abspath(configuration.vgrid_private_base),
                         os.path.abspath(configuration.vgrid_public_base)]

    configuration.daemon_conf = {
        'host': configuration.user_davs_address,
        'port': configuration.user_davs_port,
        'root_dir': os.path.abspath(configuration.user_home),
        'chmod_exceptions': chmod_exceptions,
        'chroot_exceptions': chroot_exceptions,
        'allow_password': 'password' in configuration.user_davs_auth,
        'allow_publickey': 'publickey' in configuration.user_davs_auth,
        'user_alias': configuration.user_davs_alias,
        'users': [],
        'acceptbasic': True,    # Allow basic authentication, True or False
        'acceptdigest': True,   # Allow digest authentication, True or False
        'defaultdigest': True,
        'time_stamp': 0,
        'logger': logger,
        }

    print """
Running grid davs server for user dav access to their MiG homes.

Set the MIG_CONF environment to the server configuration path
unless it is available in mig/server/MiGserver.conf
"""
    logger.info("starting WebDAV server")
    try:
        run(configuration)
    except KeyboardInterrupt:
        info_msg = "Received user interrupt"
        logger.info(info_msg)
        print info_msg
    except Exception, exc:
        logger.error("exiting on unexpected exception: %s" % exc)
