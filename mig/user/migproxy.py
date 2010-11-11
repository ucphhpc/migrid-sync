#!/bin/sh -
"exec" "python" "-O" "$0" "$@"

__doc__ = """Minimum intrusion Grid Proxy - an extension of Tiny HTTP Proxy.

This module implements GET, HEAD, POST, PUT and DELETE methods
on BaseHTTPServer, and behaves as an HTTP proxy.  The CONNECT
method is also implemented.

Any help will be greatly appreciated.		SUZUKI Hisao


Modified to only listen on local network for security reasons.
Transparently wraps select connections to MiG in SSL with configured
client certificate while leaving all other connections unchanged.
In effect it works as a local Man In The Middle (MITM) to work around
missing browser support for it.
Please refer to the README file for instructions and background.
License remains unchanged - please refer to the MIT style license
described in the distributed LICENSE file for details.
                                                Jonas Bardino
"""

__version__ = "0.2.1"

import os
import BaseHTTPServer
import select
import socket
import SocketServer
import urlparse


class MiGSSLSocket:
    """SSL socket wrapper to mimic plain socket API"""
    _sock = None
    _ssl_sock = None
    
    def __init__(self, sock, keyfile=None, certfile=None):
        self._sock = sock
	self._ssl_sock = socket.ssl(sock, keyfile=keyfile, certfile=certfile)
        self._closed = False

    def send(self, data, flags=None):
        print "DEBUG: in ssl_send"
	return self._ssl_sock.write(data)

    def recv(self, buffersize, flags=None):
        print "DEBUG: in ssl_recv"
	return self._ssl_sock.read(buffersize)

    def fileno(self):
        print "DEBUG: in ssl_fileno"
	return self._sock.fileno()

    def close(self):
        print "DEBUG: in ssl_close"
        self._ssl_sock = None
        # Try to avoid low level double free error and crash by closing any
        # open file descriptors for the socket
	os.close(self._sock.fileno())
        return self._sock.close()
    

class ProxyHandler (BaseHTTPServer.BaseHTTPRequestHandler):
    __base = BaseHTTPServer.BaseHTTPRequestHandler
    __base_handle = __base.handle

    server_version = "MiGHTTPProxy/" + __version__
    rbufsize = 0                        # self.rfile Be unbuffered
    cert_port, sid_port = 443, 443
    #key_path = os.path.expanduser('~/.mig/key.pem')
    # Path to key without passphrase
    # Use default .mig location with fallback to non-standard Android location
    key_path = os.path.expanduser('~/.mig/tmp.pem')
    if not os.path.exists(key_path):
        key_path = os.path.expanduser('/sdcard/.mig/tmp.pem')
    cert_path = os.path.expanduser('~/.mig/cert.pem')
    if not os.path.exists(cert_path):
        cert_path = os.path.expanduser('/sdcard/.mig/cert.pem')
    wrap_targets = {'www.migrid.org': {'cert_port': cert_port,
                                       'ssl_cert': cert_path,
                                       'ssl_key': key_path}, 
                    'dk.migrid.org': {'cert_port': cert_port,
                                      'ssl_cert': cert_path,
                                       'ssl_key': key_path}, 
                    'dk-cert.migrid.org': {'cert_port': cert_port,
                                           'ssl_cert': cert_path,
                                           'ssl_key': key_path},
                    'dk-sid.migrid.org': {'cert_port': cert_port,
                                          'ssl_cert': cert_path,
                                          'ssl_key': key_path}}
    wrap_ssl = False
    sock = None
    key = None
    cert = None

    def handle(self):
        (ip, port) =  self.client_address
        if hasattr(self, 'allowed_clients') and ip not in self.allowed_clients:
            self.raw_requestline = self.rfile.readline()
            if self.parse_request(): self.send_error(403)
        else:
            self.__base_handle()

    def _connect_to(self, netloc):
        i = netloc.find(':')
        if i >= 0:
            host_port = netloc[:i], int(netloc[i+1:])
        else:
            host_port = netloc, 80
	if netloc in self.wrap_targets:
	    print "\t" "wrapping connection to %s in ssl" % netloc
	    host_port = host_port[0], self.wrap_targets[netloc]['cert_port']
	    self.wrap_ssl = True
            self.key = self.wrap_targets[netloc]['ssl_key']
            self.cert = self.wrap_targets[netloc]['ssl_cert']
        print "\t" "connect to %s:%d" % host_port
        try: 
	    self.sock.connect(host_port)
	    if self.wrap_ssl:
		self.sock = MiGSSLSocket(self.sock, keyfile=self.key,
                                         certfile=self.cert)
        except socket.error, arg:
	    print "\t" "socket error:" % arg
            try: msg = arg[1]
            except: msg = arg
            self.send_error(404, msg)
            return 0
        return 1

    def do_CONNECT(self):
        print "DEBUG: in connect"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if self._connect_to(self.path):
                self.log_request(200)
                self.wfile.write(self.protocol_version +
                                 " 200 Connection established\r\n")
                self.wfile.write("Proxy-agent: %s\r\n" % self.version_string())
                self.wfile.write("\r\n")
                self._read_write(300)
        finally:
            print "\t" "bye"
            self.sock.close()
	    self.sock = None
            self.connection.close()

    def do_GET(self):
        print "DEBUG: in get"
        (scm, netloc, path, params, query, fragment) = urlparse.urlparse(
            self.path, 'http')
        if scm != 'http' or fragment or not netloc:
            self.send_error(400, "bad url %s" % self.path)
            return
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if self._connect_to(netloc):
                self.log_request()
                self.sock.send("%s %s %s\r\n" % (
                    self.command,
                    urlparse.urlunparse(('', '', path, params, query, '')),
                    self.request_version))
                self.headers['Connection'] = 'close'
                del self.headers['Proxy-Connection']
                for key_val in self.headers.items():
                    self.sock.send("%s: %s\r\n" % key_val)
                self.sock.send("\r\n")
                self._read_write()
        except socket.sslerror:
            pass
        finally:
            print "\t" "bye"
            self.sock.close()
	    self.sock = None
            self.connection.close()

    def _read_write(self, max_idling=20):
        iw = [self.connection, self.sock]
        ow = []
        count = 0
        while 1:
            count += 1
            (ins, _, exs) = select.select(iw, ow, iw, 3)
            if exs: break
            if ins:
                for i in ins:
                    if i is self.sock:
                        out = self.connection
                    else:
                        out = self.sock
                    data = i.recv(8192)
                    if data:
                        out.send(data)
                        count = 0
            else:
                print "\t" "idle", count
            if count == max_idling: break

    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT  = do_GET
    do_DELETE=do_GET

class ThreadingHTTPServer (SocketServer.ThreadingMixIn,
                           BaseHTTPServer.HTTPServer): pass


class MiGProxy(ThreadingHTTPServer):
    """HTTP(S) Proxy listening only on local interface but forwarding
    connections on any available internet interface. Connections to a
    set of configured MiG URLs are transparently wrapped in SSL with 
    client certificate while all other connections are left alone.
    """
    def __init__(self, server_address, handler):
        # Force access from local interface only using method from
        # http://code.activestate.com/recipes/439094/
        # to find and use only the IP address of the loopback device
        import fcntl, struct
        # We could support other device only by changing "lo" to 
        # another device name
        device_name = "lo"
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen_address = socket.inet_ntoa(fcntl.ioctl(
            s.fileno(), 0x8915,  # SIOCGIFADDR
            struct.pack('256s', device_name))[20:24])
        ThreadingHTTPServer.__init__(self, (listen_address, server_address[1]), handler)


if __name__ == '__main__':
    from sys import argv
    if argv[1:] and argv[1] in ('-h', '--help'):
        print argv[0], "[port [allowed_client_name ...]]"
    else:
        if argv[2:]:
            allowed = []
            for name in argv[2:]:
                client = socket.gethostbyname(name)
                allowed.append(client)
                print "Accept: %s (%s)" % (client, name)
            ProxyHandler.allowed_clients = allowed
            del argv[2:]
        else:
            print "Any clients will be served..."
            
        BaseHTTPServer.test(ProxyHandler, MiGProxy)
