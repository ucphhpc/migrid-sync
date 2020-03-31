/*
 * migauthhandler.c - C <-> Python wrappers for MiG user authentication
 * Copyright (C) 2003-2020  The MiG Project lead by Brian Vinter
 *
 * This file is part of MiG
 *
 * MiG is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 * 
 * MiG is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
 * USA.
 */

/*
 * Helpers for MiG python auth handling
 */

#include <stdlib.h>
#include <stdarg.h>
#include <stdbool.h>
#include <string.h>
#include <dlfcn.h>
#include <time.h>
#include <Python.h>
#include "migauth.h"

#define MAX_PYCMD_LENGTH (2048)

#define MIG_INVALID_USERNAME        (0x000001)
#define MIG_INVALID_USER            (0x000002)
#define MIG_SKIP_TWOFA_CHECK        (0x000004)
#define MIG_VALID_TWOFA             (0x000008)
#define MIG_AUTHTYPE_DISABLED       (0x000010)
#define MIG_AUTHTYPE_ENABLED        (0x000020)
#define MIG_INVALID_AUTH            (0x000040)
#define MIG_VALID_AUTH              (0x000080)
#define MIG_EXCEEDED_RATE_LIMIT     (0x000100)
#define MIG_EXCEEDED_MAX_SESSIONS   (0x000200)
#define MIG_USER_ABUSE_HITS         (0x000400)
#define MIG_PROTO_ABUSE_HITS        (0x000800)
#define MIG_MAX_SECRET_HITS         (0x001000)
#define MIG_SKIP_NOTIFY             (0x002000)
#define MIG_AUTHTYPE_PASSWORD       (0x004000)

#ifndef MIG_HOME
#define MIG_HOME "/home/mig/mig"
#endif

#ifndef MIG_CONF
#define MIG_CONF MIG_HOME"/server/MiGserver.conf"
#endif

#ifndef RATE_LIMIT_EXPIRE_DELAY
#define RATE_LIMIT_EXPIRE_DELAY 120
#endif

void *libpython_handle = NULL;
PyObject *py_main = NULL;

static void pyrun(const char *cmd, ...)
{
    char pycmd[MAX_PYCMD_LENGTH];
    va_list args;
    va_start(args, cmd);
    vsnprintf(pycmd, MAX_PYCMD_LENGTH, cmd, args);
    va_end(args);
    int pyres = PyRun_SimpleString(pycmd);
    if (pyres == 0) {
        WRITELOGMESSAGE(LOG_DEBUG, "pyrun OK: %s\n", pycmd);
    } else {
        WRITELOGMESSAGE(LOG_ERR, "pyrun FAILED: %s\n", pycmd);
    }
}

/* Helper function that writes messages to MiG authlog */

static bool mig_pyinit()
{
    // https://stackoverflow.com/questions/11842920/undefined-symbol-pyexc-importerror-when-embedding-python-in-c/50489814#50489814
    if (libpython_handle != NULL) {
        WRITELOGMESSAGE(LOG_DEBUG, "Python already initialized\n");
    } else {
        libpython_handle = dlopen("libpython2.7.so", RTLD_LAZY | RTLD_GLOBAL);
        Py_SetProgramName("pam-mig");
        Py_Initialize();
        if (!Py_IsInitialized()) {
            WRITELOGMESSAGE(LOG_ERR,
                            "Failed to initialize Python interpreter\n");
            return false;
        }
        py_main = PyImport_AddModule("__main__");
        if (py_main == NULL) {
            WRITELOGMESSAGE(LOG_ERR, "Failed to find Python __main__\n");
            return false;
        }
        pyrun("import os");
        pyrun("os.environ['MIG_CONF'] = '%s';", MIG_CONF);
        pyrun("import sys");
        pyrun("sys.path.append('%s')", MIG_HOME);
        pyrun("from shared.griddaemons.sftp import hit_rate_limit");
        pyrun("from shared.griddaemons.sftp import default_username_validator");
        pyrun("from shared.griddaemons.sftp import validate_auth_attempt");
        pyrun("from shared.griddaemons.sftp import active_sessions");
        pyrun("from shared.griddaemons.sftp import expire_rate_limit");
        pyrun
            ("from shared.logger import daemon_logger, register_hangup_handler");
        pyrun("from shared.conf import get_configuration_object");
        pyrun("from shared.pwhash import scramble_digest");
        pyrun("configuration = get_configuration_object(skip_log=True)");
        pyrun("log_level = configuration.loglevel");
        pyrun
            ("logger = daemon_logger('sftp-subsys', configuration.user_sftp_subsys_log, configuration.loglevel)");
        pyrun("configuration.logger = logger");
    }
    return true;
}

static bool mig_pyexit()
{
    if (libpython_handle == NULL) {
        WRITELOGMESSAGE(LOG_DEBUG, "Python already finalized\n");
    } else {
        Py_Finalize();
        dlclose(libpython_handle);
        libpython_handle = NULL;
    }
    return true;
}

static char *mig_scramble_digest(const char *key)
{
    char *digest = NULL;
    pyrun("digest = scramble_digest(configuration.site_digest_salt, '%s')",
          key);
    PyObject *py_digest = PyObject_GetAttrString(py_main, "digest");
    if (py_digest == NULL) {
        WRITELOGMESSAGE(LOG_ERR, "Missing python variable: digest\n");
    } else {
        digest = PyString_AsString(py_digest);
        Py_DECREF(py_digest);
    }
    return digest;
}

static int mig_expire_rate_limit()
{
    int result = 0;
    pyrun
        ("expired = expire_rate_limit(configuration, 'sftp-subsys', expire_delay=%d)",
         RATE_LIMIT_EXPIRE_DELAY);
    PyObject *py_expired = PyObject_GetAttrString(py_main, "expired");
    if (py_expired == NULL) {
        WRITELOGMESSAGE(LOG_ERR, "Missing python variable: expired\n");
    } else {
        result = PyInt_AsLong(py_expired);
        Py_DECREF(py_expired);
    }
    return result;
}

static bool mig_hit_rate_limit(const char *username, const char *address)
{
    bool result = false;
    pyrun
        ("exceeded_rate_limit = hit_rate_limit(configuration, 'sftp-subsys', '%s', '%s')",
         address, username);
    PyObject *py_exceeded_rate_limit =
        PyObject_GetAttrString(py_main, "exceeded_rate_limit");
    if (py_exceeded_rate_limit == NULL) {
        WRITELOGMESSAGE(LOG_ERR,
                        "Missing python variable: py_exceeded_rate_limit\n");
    } else {
        result = PyObject_IsTrue(py_exceeded_rate_limit);
        Py_DECREF(py_exceeded_rate_limit);
    }
    return result;
}

static bool mig_exceeded_max_sessions(const char *username, const char *address)
{
    bool result = false;
    int active_count = 0;
    int max_sftp_sessions = 0;

    pyrun("active_count = active_sessions(configuration, 'sftp-subsys', '%s')",
          username);
    PyObject *py_active_count = PyObject_GetAttrString(py_main, "active_count");
    if (py_active_count == NULL) {
        WRITELOGMESSAGE(LOG_ERR, "Missing python variable: py_active_count\n");
    } else {
        active_count = PyInt_AsLong(py_active_count);
        Py_DECREF(py_active_count);
    }
    pyrun("sftp_max_sessions = configuration.user_sftp_max_sessions");
    PyObject *py_max_sftp_sessions =
        PyObject_GetAttrString(py_main, "sftp_max_sessions");
    if (py_max_sftp_sessions == NULL) {
        WRITELOGMESSAGE(LOG_ERR,
                        "Missing python variable: py_max_sftp_sessions\n");
    } else {
        max_sftp_sessions = PyInt_AsLong(py_max_sftp_sessions);
        Py_DECREF(py_max_sftp_sessions);
    }
    if (max_sftp_sessions > 0 && active_count >= max_sftp_sessions) {
        result = true;
    } else {
        result = false;
    }
    return result;
}

static bool mig_validate_username(const char *username)
{
    bool result = false;
    pyrun("valid_username = default_username_validator(configuration, '%s')",
          username);
    PyObject *py_valid_username =
        PyObject_GetAttrString(py_main, "valid_username");
    if (py_valid_username == NULL) {
        WRITELOGMESSAGE(LOG_ERR,
                        "Missing python variable: py_valid_username\n");
    } else {
        result = PyObject_IsTrue(py_valid_username);
        Py_DECREF(py_valid_username);
    }
    return result;
}

static bool register_auth_attempt(const unsigned int mode,
                                  const char *username,
                                  const char *address, const char *secret)
{
    bool result = false;
    WRITELOGMESSAGE(LOG_DEBUG,
                    "mode: 0x%X, username: %s, address: %s, secret: %s\n",
                    mode, username, address, secret);
    char pycmd[MAX_PYCMD_LENGTH] =
        "(authorized, disconnect) = validate_auth_attempt(configuration, 'sftp-subsys', ";
    char pytmp[MAX_PYCMD_LENGTH];
    if (mode & MIG_AUTHTYPE_PASSWORD) {
        strncat(&pycmd[0], "'password', ", MAX_PYCMD_LENGTH - strlen(pycmd));
    } else {
        WRITELOGMESSAGE(LOG_ERR,
                        "register_auth_attempt: No valid auth-type in mode: 0x%X\n",
                        mode);
        return false;
    }
    strncat(&pycmd[0], "'", MAX_PYCMD_LENGTH - strlen(pycmd));
    strncat(&pycmd[0], username, MAX_PYCMD_LENGTH - strlen(pycmd));
    strncat(&pycmd[0], "', '", MAX_PYCMD_LENGTH - strlen(pycmd));
    strncat(&pycmd[0], address, MAX_PYCMD_LENGTH - strlen(pycmd));
    strncat(&pycmd[0], "', ", MAX_PYCMD_LENGTH - strlen(pycmd));
    if (secret != NULL) {
        sprintf(&pytmp[0], "secret='%s', ", secret);
        strncat(&pycmd[0], &pytmp[0], MAX_PYCMD_LENGTH - strlen(pycmd));
    }
    if (mode & MIG_INVALID_USERNAME) {
        strncat(&pycmd[0], "invalid_username=True, ",
                MAX_PYCMD_LENGTH - strlen(pycmd));
    }
    if (mode & MIG_INVALID_USER) {
        strncat(&pycmd[0], "invalid_user=True, ",
                MAX_PYCMD_LENGTH - strlen(pycmd));
    }
    if (mode & MIG_SKIP_TWOFA_CHECK) {
        strncat(&pycmd[0], "skip_twofa_check=True, ",
                MAX_PYCMD_LENGTH - strlen(pycmd));
    }
    if (mode & MIG_VALID_TWOFA) {
        strncat(&pycmd[0], "valid_twofa=True, ",
                MAX_PYCMD_LENGTH - strlen(pycmd));
    }
    if (mode & MIG_AUTHTYPE_DISABLED) {
        strncat(&pycmd[0], "authtype_enabled=False, ",
                MAX_PYCMD_LENGTH - strlen(pycmd));
    }
    if (mode & MIG_AUTHTYPE_ENABLED) {
        strncat(&pycmd[0], "authtype_enabled=True, ",
                MAX_PYCMD_LENGTH - strlen(pycmd));
    }
    if (mode & MIG_VALID_AUTH) {
        strncat(&pycmd[0], "valid_auth=True, ",
                MAX_PYCMD_LENGTH - strlen(pycmd));
    }
    if (mode & MIG_INVALID_AUTH) {
        strncat(&pycmd[0], "valid_auth=False, ",
                MAX_PYCMD_LENGTH - strlen(pycmd));
    }
    if (mode & MIG_EXCEEDED_RATE_LIMIT) {
        strncat(&pycmd[0], "exceeded_rate_limit=True, ",
                MAX_PYCMD_LENGTH - strlen(pycmd));
    }
    if (mode & MIG_EXCEEDED_MAX_SESSIONS) {
        strncat(&pycmd[0], "exceeded_max_sessions=True, ",
                MAX_PYCMD_LENGTH - strlen(pycmd));
    }
    if (mode & MIG_USER_ABUSE_HITS) {
        strncat(&pycmd[0], "user_abuse_hits=True, ",
                MAX_PYCMD_LENGTH - strlen(pycmd));
    }
    if (mode & MIG_PROTO_ABUSE_HITS) {
        strncat(&pycmd[0], "proto_abuse_hits=True, ",
                MAX_PYCMD_LENGTH - strlen(pycmd));
    }
    if (mode & MIG_MAX_SECRET_HITS) {
        strncat(&pycmd[0], "max_secret_hits=True, ",
                MAX_PYCMD_LENGTH - strlen(pycmd));
    }
    if (mode & MIG_SKIP_NOTIFY) {
        strncat(&pycmd[0], "skip_notify=True, ",
                MAX_PYCMD_LENGTH - strlen(pycmd));
    }
    strncat(&pycmd[0], ")", MAX_PYCMD_LENGTH - strlen(pycmd));
    if (MAX_PYCMD_LENGTH == strlen(pycmd)) {
        WRITELOGMESSAGE(LOG_ERR, "register_auth_attempt: pycmd overflow\n");
        return false;
    }
    pyrun(&pycmd[0]);
    PyObject *py_authorized = PyObject_GetAttrString(py_main, "authorized");
    if (py_authorized == NULL) {
        WRITELOGMESSAGE(LOG_ERR, "Missing python variable: py_authorized\n");
    } else {
        result = PyObject_IsTrue(py_authorized);
        Py_DECREF(py_authorized);
    }

    return result;
}
