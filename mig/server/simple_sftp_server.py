#!/usr/bin/python

# This is the MIT license:
# http://www.opensource.org/licenses/mit-license.php

# Copyright (c) 2009 Digital Achievement Incorporated and contributors.

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

#
# This code is a modified version of the sftp server from
# http://achievewith.us/hg/simple_sftp_server
# Modifications for MiG use are all
# Copyright (C) 2010  The MiG Project lead by Brian Vinter
#

import base64
import logging
import os
import paramiko
import paramiko.util
import socket
import sys
import tempfile
import threading
import time
from optparse import OptionParser
from StringIO import StringIO

#paramiko.util.log_to_file("paramiko.log")
logging.getLogger("paramiko").setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("sftpserver")

configuration_template = """# simple sftp_server.py configuration

# Bind to all interfaces by default
address = ""
port = 2222
root_dir = "/path/to/your/mig/state/user_home"

# The chroot option will set the effective root
# directory to "%s/%s" % (root_dir, user.user_name)
# it defaults to True
#
# users = [User(username='some_user', password='password', chroot=True),
#         User(username='another', password='password'),
#         User(username='admin', password='password', chroot=False),]

# Now it's your turn:
users = []

# Optional sftp implementation.  Will default to ssftps.server:SimpleSftpServer
# sftp_implementation = ""

host_rsa_key = \"\"\"
-----BEGIN RSA PRIVATE KEY-----
MIIEoQIBAAKCAQEArJqP/6XFBa88x/DUootMmSzYa3MxcTV9FjNYUomqbQlGzuHa
n1Ef6YClJuBWu1eCdZfoeUoa56du1XV2eGKdDjWEqyie2uZ8RZeJZvT1wCuyvO6X
E143A4z3xHi6R6Qi7rimJFpxL6lGmYHx64wQgL93FXTe/HrmdPoxGeTEf+PnN/PV
Se321o/Ludqfu+8cldbuKaYRRZJSPT+sIMafvErL86I3JShYqaBjXcic8yYgaAZx
6Ieu6A19UJzZurQpCdnWoMMLEQ1EgU4LIkUg+SzVSTpBDV3uiBB0+iOdG+v0v+RO
53GAcKRx9Y38vQazpdAw4AhX97Hj6c/WcpET+QIBIwKCAQBsfmkkWZHJDxBDKao6
SO5RpyjzFTUFVNJIeAuhmFx/DSUxlUeXV5Bm4yX7Le1f0JslWCu59BDpYe3lQoT7
NqvdC7J6NspAc56SJLzEX3Xmgd4QW3Tnmk53QqpePUHj44Or/wlYreC+3240mtKU
DuXNRSZIAFGmBBvUgAGbP1bxTGRShWlebnDsEFuv8BnrjTB1GBN3SshgwTuApete
7yPPNNPhiAMHN27z5p5sMDU43+FgZd8GEJbHckmriIcwLr1Q0iwlmsrYRndRnA7u
bbl9D5SwTROE8mtACHBLOdkJ5glfp68GhKjZ+HPTkI+fKqv70DOB7TsP9F4EsNO/
FQUzAoGBANo2ScHL6RFHUpztE0+dc9g9Yk4S+tjW1sVHMOWGN/KmwiqBIwiusvWY
vXf/4i/kbehGnwedAtfRmjQSJbIyOEhMt1MxaN0Wn44YUgoWCbfplJG1Tmk25eEX
VrwOahTtzDGibtHNNmi97D2dFR7V36mhECTqwyzEE142yGrRJnLPAoGBAMp+YXd/
D2B0xhFMJmyzYHdBFCQHbm4DWZcGey09tSKo+mei+EDq+knSrjUmJV40PMXwxVjw
anLZJjEh72e71G28jlR5WEhciT5nJqN5pB8Oc9cHFCGC9mLQrEwW9MYqAz/WvCx4
lpa1Cge2b/lp7snc3Yt4BfAl35MIqElOg163AoGAGPBC8ZOlm5MfYmQ8uKRHwPES
jJR0cI2U41iX37eRXY9mpcWdmpefbIZ8DbbYBXkxIdwvbpWZ7Md/Vmh5VjGgCENI
JsPReFpbYLJShM9RkVyGAgYXlv71s1Mf2vpVRDhvG52JAgjTBKf9veYRCtadN/Um
ap58tKixwZ/cY/qlTvMCgYBFbSi7QYGdad2CRf6LqzcEUNO0lNVnjB63b++3vWKs
zDiYj6WSmbTmHFj8R5fIhvBD3YV9lEHA+f53PtW9KnS36OBXeg+jx/SKbIJGrVzX
cqtfqqfQ+bOPmACPHdBD8SWvfNLNayxQ7Z0J9Wg4QZOy7KO6yhCqG50cd/8vE5rB
YwKBgQCH9mHpdfORUCXVt1QScw29mhLskx5SA/9vU4lrKpwr0Kkce+d0Cex14jWG
cLz1fOlcctHsIQBMFxEBR0dM7RNX/kdvWfhiPDl1VgDQIyrAEC9euig92hKhmA2E
Myw1d5t46XP97y6Szrhcsrt15pmSKD+zLYXD26qoxKJOP9a6+A==
-----END RSA PRIVATE KEY-----
\"\"\"

"""

class User(object):
    def __init__(self, username, password, 
                 chroot=True, home=None, public_key=None):
        self.username = username
        self.password = password
        self.chroot = chroot
        self.public_key = public_key
        if type(self.public_key) in (str, unicode):
            bits = base64.decodestring(self.public_key.split(' ')[1])
            msg = paramiko.Message(bits)
            key = paramiko.RSAKey(msg)
            self.public_key = key

        self.home = home
        if self.home is None:
            self.home = self.username

class SFTPHandle(paramiko.SFTPHandle):
    def __init__(self, flags=0, path=None):
        paramiko.SFTPHandle.__init__(self, flags)
        self.path = path
        if(flags == 0):
            self.readfile = open(path, "r")
        else:
            self.writefile = open(path, "w")

# We don't need subversion support
'''
class SvnSFTPHandle(SFTPHandle):
    def __init__(self, flags=0, path=None):
        paramiko.SFTPHandle.__init__(self, flags)
        self.path = path
        if(flags == 0):
            self.readfile = open(path, "r")
        else:
            self.writefile = open(path, "w")

    def close(self):
        paramiko.SFTPHandle.close(self)
        
        writefile = getattr(self, 'writefile', None)
        if writefile is not None:
            writefile.close()
            os.system("svn add %s" % self.path)
            os.system("svn commit -m 'auto add' %s" % (self.path))
'''

class SimpleSftpServer(paramiko.SFTPServerInterface):
    def __init__(self, server, transport, fs_root, users, *largs, **kwargs):
        self.transport = transport
        self.root = fs_root
        self.user_name = self.transport.get_username()
        self.users = users

        if self.users[self.user_name].chroot:
            self.root = "%s/%s" % (self.root, self.users[self.user_name].home)

    def get_fs_path(self, sftp_path):
        real_path = "%s/%s" % (self.root, sftp_path)
        real_path = real_path.replace('//', '/')
        
        if not os.path.realpath(real_path).startswith(self.root):
            raise Exception("Invalid path")

        logger.debug("real_path :: %s" % real_path)
        return(real_path)

    def open(self, path, flags, attr):
        real_path = self.get_fs_path(path)
        logger.debug("open %s :: %s" % (path, real_path))
        #logger.debug("open %s :: %d" % (path, attr))
        return(SFTPHandle(flags, real_path))

    def list_folder(self, path):
        real_path = self.get_fs_path(path)
        logger.debug("list_folder %s :: %s" % (path, real_path))
        rc = []
        for filename in os.listdir(real_path):
            full_name = ("%s/%s" % (real_path, filename)).replace("//", "/")
            rc.append(paramiko.SFTPAttributes.from_stat(os.stat(full_name), filename.replace(self.root, '')))
        return rc

    def stat(self, path):
        real_path = self.get_fs_path(path)
        logger.debug("stat %s :: %s" % (path, real_path))
        return paramiko.SFTPAttributes.from_stat(os.stat(real_path), path)

    def lstat(self, path):
        real_path = self.get_fs_path(path)
        logger.debug("lstat %s :: %s" % (path, real_path))
        return paramiko.SFTPAttributes.from_stat(os.stat(real_path), path)

    def remove(self, path):
        real_path = self.get_fs_path(path)
        logger.debug("remove %s :: %s" % (path, real_path))
        os.remove(real_path)
        return paramiko.SFTP_OK

    def rename(self, oldpath, newpath):
        logger.debug("rename %s %s" % (oldpath, newpath))
        real_oldpath = self.get_fs_path(oldpath)
        real_newpath = self.get_fs_path(newpath)
        # print "rename %s %s" % (real_oldpath, real_newpath)
        os.rename(real_oldpath, real_newpath)
        return paramiko.SFTP_OK

    def mkdir(self, path, mode):
        logger.debug("mkdir %s" % path)
        real_path = self.get_fs_path(path)
	# Force MiG default mode
        os.mkdir(real_path, 0o755)
        return paramiko.SFTP_OK

    def rmdir(self, path):
        logger.debug("rmdir %s" % path)
        real_path = self.get_fs_path(path)
        os.rmdir(real_path)
        return paramiko.SFTP_OK

    def chattr(self, path, attr):
        logger.debug("chattr %s" % path)
	# Prevent users from messing with access modes
        return paramiko.SFTP_OP_UNSUPPORTED
         
    #def canonicalize(self, path):
    #    print "canonicalize %s" % path
    #    return paramiko.SFTPServerInterface.canoncialize(self, path)

    def readlink(self, path):
        logger.debug("readlink %s" % path)
        real_path = self.get_fs_path(path)
	relative_path = os.readlink(path).replace(self.root, '')
	return relative_path

    def symlink(self, target_path, path):
        logger.debug("symlink %s" % target_path)
	# Prevent users from creating symlinks for security reasons
        return paramiko.SFTP_OP_UNSUPPORTED

# We don't need subversion support
'''
class SubversionSftpServer(SimpleSftpServer):
    def __init__(self, *largs, **kwargs):
        SimpleSftpServer.__init__(self, *largs, **kwargs)

    def open(self, path, flags, attr):
        real_path = self.get_fs_path(path)
        logger.debug("open %s :: %s" % (path, real_path))
        #logger.debug("open %s :: %d" % (path, attr))
        return(SvnSFTPHandle(flags, real_path))

    def remove(self, path):
        real_path = self.get_fs_path(path)
        logger.debug("remove %s :: %s" % (path, real_path))
        os.system("svn del %s" % real_path)
        os.system("svn commit -m 'auto commit for %s' %s" % (self.user_name, real_path))
        # os.remove(real_path)
        return 0

    def rename(self, oldpath, newpath):
        logger.debug("rename.svn %s %s" % (oldpath, newpath))
        real_oldpath = SimpleSftpServer.get_fs_path(self, oldpath)
        real_newpath = SimpleSftpServer.get_fs_path(self, newpath)
        logger.debug("rename %s %s" % (real_oldpath, real_newpath))
        # os.rename(real_oldpath, real_newpath)
        os.system("svn mv %s %s" % (real_oldpath, real_newpath))
        os.system("svn commit -m 'auto commit for %s' %s %s" % (self.user_name, real_oldpath, real_newpath))
        return 0


class IntegrationTestSftpServer(SimpleSftpServer):
    def __init__(self, *largs, **kwargs):
        SimpleSftpServer.__init__(self, *largs, **kwargs)

        oldroot = self.root
        tempdir = tempfile.mkdtemp()
        os.system("cp -r %s/* %s" % (self.root, tempdir))
        self.root = tempdir
        logger.info("Changing root from %s to %s" % (oldroot, self.root))

    def session_ended(self):
        logger.info("Session ended, cleaning up %s" % self.root)
        os.system("rm -rf %s" % self.root)
'''


class SimpleSSHServer(paramiko.ServerInterface):
    def __init__(self, users):
        self.event = threading.Event()
        self.users = users
        self.authenticated_user = None

    def check_channel_request(self, kind, chanid):
        logger.info("channel_request: %s, %s" % (kind, chanid))
        return paramiko.OPEN_SUCCEEDED

    def check_auth_password(self, username, password):
        if username in self.users:
            if self.users[username].password == password:
                logger.info("Authenticated %s" % username)
                return paramiko.AUTH_SUCCESSFUL
        logger.info("Rejected %s" % username)
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        if username in self.users:
            u = self.users[username]
            if u.public_key is not None:
                if u.public_key.get_base64() == key.get_base64():
                    logger.info("Public key match for %s" % username)
                    return paramiko.AUTH_SUCCESSFUL
        logger.info('Public key authentication failed')
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'password,publickey'

    def get_authenticated_user(self):
        return self.authenticated_user

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    #def check_channel_subsystem_request(self, channel, name):
    #    print channel
    #    print name
    #    self.event.set()
    #    return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth,
                                  pixelheight, modes):
        return True


def accept_client(client, addr, root_dir, users, host_rsa_key, conf={}):
    usermap = {}
    for u in users:
        usermap[u.username] = u

    host_key_file = StringIO(host_rsa_key)
    host_key = paramiko.RSAKey(file_obj=host_key_file)
    transport = paramiko.Transport(client)
    transport.load_server_moduli()
    transport.add_server_key(host_key)

    if "sftp_implementation" in conf:
        mod_name, class_name = conf['sftp_implementation'].split(':')
        fromlist = None
        try:
            parent = mod_name[0:mod_name.rindex('.')]
            fromlist = [parent]
        except:
            pass
        mod = __import__(mod_name, fromlist=fromlist)
        impl = getattr(mod, class_name)
        logger.info("Custom implementation: %s" % conf['sftp_implementation'])
    else:
        impl = SimpleSftpServer
    transport.set_subsystem_handler("sftp", paramiko.SFTPServer, sftp_si=impl, transport=transport, fs_root=root_dir, users=usermap)

    server = SimpleSSHServer(users=usermap)
    transport.start_server(server=server)
    channel = transport.accept()
    while(transport.is_active()):
        time.sleep(3)

    username = server.get_authenticated_user()
    if username is not None:
        user = usermap[username]
        os.system("svn commit -m 'committing user session for %s' %s" % (username, root_dir + "/" + user.home))

def refresh_users(conf):
    '''Reload users from conf if it changed on disk'''
    if conf['time_stamp'] >= os.path.getmtime(conf['conf_path']):
        return conf
    try:
        cur_conf = {}
        execfile(conf['conf_path'], globals(), cur_conf)
        conf['users'] = cur_conf['users']
        conf['time_stamp'] = time.time()
        logger.info("Refreshed users from configuration")
    except Exception as exc:
        logger.error("Configuration reload failed: %s" % exc)
    return conf

def start_service(configuration):
     server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
     # Allow reuse of socket to avoid TCP time outs
     server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
     server_socket.bind((configuration['address'], configuration['port']))
     server_socket.listen(10)

     logger.info("Accepting connections")
     while True:
         client, addr = server_socket.accept()
         # automatic reload of users
         configuration = refresh_users(configuration)
         t = threading.Thread(target=accept_client, args=[client, 
                                                          addr, 
                                                          configuration['root_dir'],
                                                          configuration['users'],
                                                          configuration['host_rsa_key'],
                                                          configuration,])
         t.start()

def create_configuration_file(path):
    cf = open(path, "w")
    cf.write(configuration_template)
    cf.close()


def main():
    usage = """usage: %prog [options]
 One of --config-file or --new-config must be specified"""
    oparser = OptionParser(usage=usage)
    oparser.add_option("-a", "--address", dest="address",
                       help="listen on ADDRESS (leave empty for all)", metavar="ADDRESS")
    oparser.add_option("-p", "--port", dest="port",
                       help="listen on PORT", metavar="PORT")
    oparser.add_option("-c", "--config-file", dest="config_file",
                       help="configuration file path")
    oparser.add_option("-n", "--new-config", dest="new_config",
                       help="createa a new configuration file at the provided path")

    (options, args) = oparser.parse_args()

    if (options.config_file is None) and (options.new_config is None):
        oparser.print_help()
        sys.exit(-1)

    if (options.config_file is not None) and (options.new_config is not None):
        oparser.print_help()
        sys.exit(-1)

    if options.new_config is not None:
        logger.info("Creating a configuration file at %s" % options.new_config)
        create_configuration_file(options.new_config)

    if options.config_file is not None:
        logger.info("Starting SFTP service")
        config = {}
        execfile(options.config_file, globals(), config)
        config['conf_path'] = options.config_file
        config['time_stamp'] = time.time()
        start_service(config)


if __name__ == "__main__":
    main()
