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

#include <openssl/ssl.h>

/* NOTE: care is needed to support both legacy and modern versions of OpenSSL,
   as 1.1+ made a number of data structures opaque and thus removed direct
   access to e.g. session id and master key.
   https://wiki.openssl.org/index.php/OpenSSL_1.1.0_Changes

   Examples of working with the 1.1+ getter methods can be found e.g. in the
   sslkeylog_get_master_key function from
   https://github.com/segevfiner/sslkeylog/blob/master/_sslkeylog.c
*/

/* TODO: can we *include* these defs instead to eliminate the versioning ? */

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
	/* For supporting both legacy and 1.1+ versions of OpenSSL */
	SSL_SESSION *ssl_session = NULL;
	const unsigned char *ssl_session_id = NULL;

	if (!PyArg_ParseTuple(args, "|O:session_id", &pysslobject))
		return NULL;
	pyssl = (PySSLObject *) pysslobject;

	/* TODO: add proper error checking like in 
	   https://github.com/segevfiner/sslkeylog/blob/master/_sslkeylog.c#L145
	*/
#if OPENSSL_VERSION_NUMBER < 0x10100000L 
	/* For legacy OpenSSL support */
	ssl_session = pyssl->ssl->session;
	ssl_session_id = ssl_session->session_id;
#else
	/* For OpenSSL-1.1+ support */
	unsigned int id_len;
	ssl_session = SSL_get_session(pyssl->ssl);
	ssl_session_id = SSL_SESSION_get_id(ssl_session, &id_len);
#endif

	/*
	   fprintf(stderr, "\npysslobject: %p\n", pysslobject);
	   fprintf(stderr, "\npyssl: %p\n", pyssl);
	   fprintf(stderr, "\npyssl->ssl: %p\n", pyssl->ssl);
	   fprintf(stderr, "\nssl_session: %p\n", ssl_session);
	   fprintf(stderr, "\nssl_session_id: %s\n", ssl_session_id);
	*/

#if PY_MAJOR_VERSION >= 3
	/* For python 3+ support */
	session_id = PyBytes_FromStringAndSize((const char *)ssl_session_id,
					       SSL_MAX_SSL_SESSION_ID_LENGTH);
#else
	/* For python 2 support */
	session_id = PyString_FromStringAndSize((const char *)ssl_session_id,
						SSL_MAX_SSL_SESSION_ID_LENGTH);
#endif

	return session_id;
}

static PyObject *PySSLSESSION_master_key(PyObject * self, PyObject * args)
{
	PyObject *pysslobject = Py_None;
	PyObject *master_key = Py_None;
	PySSLObject *pyssl = NULL;
	/* For supporting both legacy and 1.1+ versions of OpenSSL */
	SSL_SESSION *ssl_session = NULL;
	unsigned char *ssl_master_key = NULL;

	if (!PyArg_ParseTuple(args, "|O:master_key", &pysslobject))
		return NULL;
	pyssl = (PySSLObject *) pysslobject;

	/* TODO: add proper error checking like in 
	   https://github.com/segevfiner/sslkeylog/blob/master/_sslkeylog.c#L145
	*/
#if OPENSSL_VERSION_NUMBER < 0x10100000L 
	/* For legacy OpenSSL support */
	ssl_session = pyssl->ssl->session;
	ssl_master_key = ssl_session->master_key;
#else
	/* For OpenSSL-1.1+ support */
	unsigned char tmp_ssl_master_key[SSL_MAX_MASTER_KEY_LENGTH];
	ssl_master_key = (unsigned char *)&tmp_ssl_master_key;
	ssl_session = SSL_get_session(pyssl->ssl);
	SSL_SESSION_get_master_key(ssl_session, ssl_master_key, 
	                           SSL_MAX_MASTER_KEY_LENGTH);
#endif

	/*
	   fprintf(stderr, "\npysslobject: %p\n", pysslobject);
	   fprintf(stderr, "\npyssl: %p\n", pyssl);
	   fprintf(stderr, "\npyssl->ssl: %p\n", pyssl->ssl);
	   fprintf(stderr, "\nssl_session: %p\n", ssl_session);
	   fprintf(stderr, "\nssl_master_key: %s\n", ssl_master_key);
	 */

#if PY_MAJOR_VERSION >= 3
	/* For python 3+ support */
	master_key = PyBytes_FromStringAndSize((const char *)ssl_master_key,
					       SSL_MAX_MASTER_KEY_LENGTH);
#else
	/* For python 2 support */
	master_key = PyString_FromStringAndSize((const char *)ssl_master_key,
						SSL_MAX_MASTER_KEY_LENGTH);
#endif

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
#if PY_MAJOR_VERSION >= 3
	/* For python 3+ support */
	static struct PyModuleDef moduledef = {
		PyModuleDef_HEAD_INIT,
		"_sslsession",     /* m_name */
		"SSL session module",  /* m_doc */
		-1,                  /* m_size */
		PySSLSESSIONMethods,    /* m_methods */
		NULL,                /* m_reload */
		NULL,                /* m_traverse */
		NULL,                /* m_clear */
		NULL,                /* m_free */
	};
	PyModule_Create(&moduledef);
#else
	/* For python 2 support */
	Py_InitModule3("_sslsession", PySSLSESSIONMethods,
		       "SSL session module");
#endif
}
