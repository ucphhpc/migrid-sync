/* --- BEGIN_HEADER ---

_sslsession - Shared library functions for SSL session information
Copyright (C) 2003-2018  The MiG Project lead by Brian Vinter

This file is part of MiG.

MiG is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

MiG is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

-- END_HEADER --- */

#include <Python.h>

#include "openssl/ssl.h"

/******************************************************** 
Copied from 'Python-2.7.5/Modules/socketmodule.h' 
********************************************************/

/* The object holding a socket.  It holds some extra information,
   like the address family, which is used to decode socket address
   arguments properly. */

typedef int SOCKET_T;

typedef struct {
	PyObject_HEAD SOCKET_T sock_fd;	/* Socket file descriptor */
	int sock_family;	/* Address family, e.g., AF_INET */
	int sock_type;		/* Socket type, e.g., SOCK_STREAM */
	int sock_proto;		/* Protocol type, usually 0 */
	PyObject *(*errorhandler) (void);	/* Error handler; checks
						   errno, returns NULL and
						   sets a Python exception */
	double sock_timeout;	/* Operation timeout in seconds;
				   0.0 means non-blocking */
} PySocketSockObject;

/******************************************************** 
Copied from 'Python-2.7.5/Modules/_ssl.c' 
********************************************************/

#define X509_NAME_MAXLEN 256

typedef struct {
	PyObject_HEAD PySocketSockObject * Socket;	/* Socket on which we're layered */
	SSL_CTX *ctx;
	SSL *ssl;
	X509 *peer_cert;
	char server[X509_NAME_MAXLEN];
	char issuer[X509_NAME_MAXLEN];
	int shutdown_seen_zero;

} PySSLObject;

/******************************************************** 
END of "include copies"
********************************************************/

static PyObject *PySSLSESSION_session_id(PyObject * self, PyObject * args)
{
	PyObject *pysslobject = Py_None;
	PyObject *session_id = Py_None;
	PySSLObject *pyssl = NULL;

	if (!PyArg_ParseTuple(args, "|O:session_id", &pysslobject))
		return NULL;
	pyssl = (PySSLObject *) pysslobject;

	/*
	   fprintf(stderr, "\npysslobject: %p\n", pysslobject);
	   fprintf(stderr, "\npyssl: %p\n", pyssl);
	   fprintf(stderr, "\npyssl->ssl: %p\n", pyssl->ssl);
	   fprintf(stderr, "\npyssl->ssl->session: %p\n", pyssl->ssl->session);
	   fprintf(stderr, "\npyssl->ssl->session->session_id: %s\n", 
	   pyssl->ssl->session->session_id);
	 */

	session_id = PyString_FromStringAndSize((const char *)pyssl->ssl->
						session->session_id,
						SSL_MAX_SSL_SESSION_ID_LENGTH);

	return session_id;
}

static PyObject *PySSLSESSION_master_key(PyObject * self, PyObject * args)
{
	PyObject *pysslobject = Py_None;
	PyObject *master_key = Py_None;
	PySSLObject *pyssl = NULL;

	if (!PyArg_ParseTuple(args, "|O:master_key", &pysslobject))
		return NULL;
	pyssl = (PySSLObject *) pysslobject;

	/*
	   fprintf(stderr, "\npysslobject: %p\n", pysslobject);
	   fprintf(stderr, "\npyssl: %p\n", pyssl);
	   fprintf(stderr, "\npyssl->ssl: %p\n", pyssl->ssl);
	   fprintf(stderr, "\npyssl->ssl->session: %p\n", pyssl->ssl->session);
	   fprintf(stderr, "\npyssl->ssl->session->master_key: %s\n", 
	   pyssl->ssl->session->master_key);
	 */

	master_key = PyString_FromStringAndSize((const char *)pyssl->ssl->
						session->master_key,
						SSL_MAX_MASTER_KEY_LENGTH);

	return master_key;
}

static char session_id_docs[] = "Returns SSL session id\n";

static char master_key_docs[] = "Returns SSL session master key\n";

static PyMethodDef PySSLSESSIONMethods[] = {
	{"session_id", (PyCFunction) PySSLSESSION_session_id,
	 METH_VARARGS, session_id_docs},
	{"master_key", (PyCFunction) PySSLSESSION_master_key,
	 METH_VARARGS, master_key_docs},
	{NULL}
};

void init_sslsession(void)
{
	Py_InitModule3("_sslsession", PySSLSESSIONMethods,
		       "SSL session module");
}
