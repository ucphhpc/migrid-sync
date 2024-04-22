/* --- BEGIN_HEADER ---

lfs - Shared lustre library functions for Python lustre quota
Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter

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

/* Inspired by lustre/utils/lfs.c */
#include <stdlib.h>
#include <stdio.h>
#include <inttypes.h>
#include <getopt.h>
#include <string.h>
#include <mntent.h>
#include <unistd.h>
#include <errno.h>
#include <err.h>
#include <pwd.h>
#include <grp.h>
#include <sys/ioctl.h>
#include <sys/quota.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/param.h>
#include <sys/xattr.h>
#include <fcntl.h>
#include <dirent.h>
#include <time.h>
#include <ctype.h>
#include <libgen.h>
#include <asm/byteorder.h>
#include "lfs_project.h"
#include <libcfs/util/string.h>
#include <libcfs/util/ioctl.h>
#include <libcfs/util/parser.h>
#include <libcfs/util/string.h>
#include <lustre/lustreapi.h>
#include <linux/lustre/lustre_ver.h>
#include <linux/lustre/lustre_param.h>
#include <linux/lnet/nidstr.h>
#include <syslog.h>
#include <Python.h>

/* Define log macros */

#define STRINGIFY(x) #x
#define TOSTRING(x) STRINGIFY(x)
#if (_DEBUG == 1)
#define WRITELOGMESSAGE(priority, format, ...) \
    fprintf(stderr, #priority ": " __FILE__"("TOSTRING(__LINE__)"): " format, ##__VA_ARGS__)
#else
#define WRITELOGMESSAGE(priority, format, ...) \
    if (priority != LOG_DEBUG) fprintf(stderr, #priority ": " format, ##__VA_ARGS__)
#endif 

/* Set lustre project id */

static PyObject* lfs_set_project_id(PyObject* self, PyObject *args) {
    /* Returns tuple with:
    rc:         Return code
    */

    /* Parse python arguments int C variables */

    char                *lr_path              = NULL;
    unsigned int        lr_project_id         = 0;
    unsigned int        lr_recursive          = 0;

    // https://docs.python.org/3/c-api/arg.html
    if(!PyArg_ParseTuple(args, 
                        "sII",
                        &lr_path,
                        &lr_project_id,
                        &lr_recursive
                        )) {
        return NULL;
    }
    
    WRITELOGMESSAGE(LOG_DEBUG, "=================================================================\n");
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_set_project_id.lr_path: %s\n", lr_path);
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_set_project_id.lr_project_id: %d\n", lr_project_id);
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_set_project_id.lr_recursive: %d\n", lr_recursive);
    WRITELOGMESSAGE(LOG_DEBUG, "=================================================================\n");

    /* End: Parse python arguments int C variables */

    int                             rc      = 0;
    struct project_handle_control   phc     = { 0 };
    PyObject                        *result = NULL;

    phc.projid = lr_project_id;
    phc.assign_projid = true;
    phc.set_inherit = true;
    phc.set_projid = true;
    if (lr_recursive == 0) {
        phc.recursive = false;
    } else {
        phc.recursive = true;
    }
    WRITELOGMESSAGE(LOG_DEBUG, "=================================================================\n");
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_set_project_id.phc.projid: %d\n", phc.projid);
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_set_project_id.phc.recursive: %d\n", phc.recursive);
    WRITELOGMESSAGE(LOG_DEBUG, "=================================================================\n");
    rc = lfs_project_set(lr_path, &phc);
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_set_project_id: rc: %d\n", rc);
    // https://docs.python.org/3/c-api/arg.html
    result = Py_BuildValue("i", \
                            rc);
    return result;
}

/* Get lustre project quota */

static PyObject* lfs_get_project_quota(PyObject* self, PyObject *args) {
    /* Returns tuple with:
    rc:                 Return code
    currfiles:          Number of current files
    currspace_bytes     Number of bytes
    softlimit_bytes:    Softlimit in bytes
    hardlimit_bytes:    Hardlimit in bytes
    */

    /* Parse python arguments int C variables */

    char                *lr_path              = NULL;
    unsigned int        lr_project_id         = 0;

    // https://docs.python.org/3/c-api/arg.html
    if(!PyArg_ParseTuple(args, 
                        "sI",
                        &lr_path,
                        &lr_project_id
                        )) {
        return NULL;
    }
    
    WRITELOGMESSAGE(LOG_DEBUG, "=================================================================\n");
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_get_project_quota.lr_path: %s\n", lr_path);
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_get_project_quota.lr_project_id: %d\n", lr_project_id);
    WRITELOGMESSAGE(LOG_DEBUG, "=================================================================\n");

    /* End: Parse python arguments int C variables */

    int                             rc               = 0;
    long long unsigned int          currfiles        = 0;
    long long unsigned int          currspace_bytes  = 0;
    long long unsigned int          softlimit_bytes = 0;
    long long unsigned int          hardlimit_bytes = 0;
    struct if_quotactl              *qctl            = NULL;
    struct obd_dqblk                *dqb             = NULL;
    PyObject                        *result          = NULL;
    
    qctl = calloc(1, sizeof(*qctl) + LOV_MAXPOOLNAME + 1);
    if (!qctl) {
        rc =  -ENOMEM;
        goto out;
    }

    qctl->qc_cmd = LUSTRE_Q_GETQUOTA;
    qctl->qc_type = PRJQUOTA;
    qctl->qc_id = lr_project_id;

    rc = llapi_quotactl(lr_path, qctl);
    if (rc < 0) {
        switch (rc) {
        case -ESRCH:
            WRITELOGMESSAGE(LOG_PERROR, "Quotas are not enabled.\n");
        case -EPERM:
            WRITELOGMESSAGE(LOG_PERROR, "Permission denied.\n");
        default:
            WRITELOGMESSAGE(LOG_PERROR, "Unexpected quotactl error: %s\n",
                strerror(-rc));
        }
        goto out;
    }
    dqb = &qctl->qc_dqblk;
    currfiles = dqb->dqb_curinodes;
    currspace_bytes = dqb->dqb_curspace;
    /* NOTE:  dqb->dqb_bXlimit is set i KB */
    hardlimit_bytes = dqb->dqb_bhardlimit << 10;
    softlimit_bytes = dqb->dqb_bsoftlimit << 10;
    WRITELOGMESSAGE(LOG_DEBUG, "=================================================================\n");
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_get_project_quota.llapi_quotactl: %s: %d\n", 
        lr_path, rc);
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_get_project_quota.llapi_quotactl: %s: files: %llu\n", 
        lr_path, currfiles);
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_get_project_quota.llapi_quotactl: %s: currspace_bytes: %llu\n", 
        lr_path, currspace_bytes);
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_get_project_quota.llapi_quotactl: %s: softlimit_bytes: %llu\n", 
        lr_path, softlimit_bytes);
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_get_project_quota.llapi_quotactl: %s: hardlimit_bytes: %llu\n", 
        lr_path, hardlimit_bytes);
    WRITELOGMESSAGE(LOG_DEBUG, "=================================================================\n");
out:
    free(qctl);
    // https://docs.python.org/3/c-api/arg.html
    return Py_BuildValue("iKKKK", \
                         rc,
                         currfiles,
                         currspace_bytes,
                         softlimit_bytes,
                         hardlimit_bytes
                         );

    return result;
}

/* Set lustre project quota */

static PyObject* lfs_set_project_quota(PyObject* self, PyObject *args) {
    /* Returns tuple with:
    rc:         Return code
    */

    /* Parse python arguments int C variables */

    char                *lr_path              = NULL;
    unsigned int        lr_project_id         = 0;
    unsigned long long  lr_quota_softlimit    = 0;
    unsigned long long  lr_quota_hardlimit    = 0;

    // https://docs.python.org/3/c-api/arg.html
    if(!PyArg_ParseTuple(args, 
                        "sIKK",
                        &lr_path,
                        &lr_project_id,
                        &lr_quota_softlimit,
                        &lr_quota_hardlimit
                        )) {
        return NULL;
    }
    WRITELOGMESSAGE(LOG_DEBUG, "=================================================================\n");
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_set_project_quota.lr_path: %s\n", lr_path);
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_set_project_quota.lr_project_id: %d\n", lr_project_id);
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_set_project_quota.lr_quota_softlimit: %llu\n", lr_quota_softlimit);
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_set_project_quota.lr_quota_hardlimit: %llu\n", lr_quota_hardlimit);
    WRITELOGMESSAGE(LOG_DEBUG, "=================================================================\n");

    /* End: Parse python arguments int C variables */

    int                             rc               = 0;
    int                             qctl_len         = 0;
    unsigned int                    min_quota_limit  = 1024<<10;
    struct if_quotactl              *qctl            = NULL;
    struct obd_dqblk                *dqb             = NULL;
    PyObject                        *result          = NULL;
    

    /* Check quota limits */

    if (lr_quota_softlimit <= min_quota_limit) {
        rc = 1;
        WRITELOGMESSAGE(LOG_PERROR,
            "lfs_set_project_quota softlimit: %llu is to small, minimum allowed: %u\n"
                , lr_quota_softlimit, min_quota_limit);
        goto out;
    } else if (lr_quota_hardlimit <= min_quota_limit) {
        rc = 1;
        WRITELOGMESSAGE(LOG_PERROR,
            "lfs_set_project_quota hardlimit: %llu is to small, minimum allowed: %u\n"
                , lr_quota_hardlimit, min_quota_limit);
        goto out;
    } else if (lr_quota_softlimit > lr_quota_hardlimit) {
        rc = 1;
        WRITELOGMESSAGE(LOG_PERROR,
            "lfs_set_project_quota softlimit > hardlimit: %llu > %llu\n"
                , lr_quota_softlimit, lr_quota_hardlimit);
        goto out;
    }
    /* Allocate memory for quota struct */

    qctl_len = sizeof(*qctl) + LOV_MAXPOOLNAME + 1;
    qctl = malloc(qctl_len);
    if (!qctl) {
        rc = -ENOMEM;
        WRITELOGMESSAGE(LOG_PERROR,
            "lfs_set_project_quota: Out of memmmory\n");
        goto out;
    }

    /* Fill quota struct */

    memset(qctl, 0, qctl_len);
    qctl->qc_cmd = LUSTRE_Q_SETQUOTA;
    qctl->qc_type = PRJQUOTA;
    qctl->qc_id = lr_project_id;
    dqb = &qctl->qc_dqblk;
    dqb->dqb_valid = QIF_BLIMITS;
    /* NOTE:  dqb->dqb_bXlimit is set i KB */
    dqb->dqb_bsoftlimit = lr_quota_softlimit >> 10;
    dqb->dqb_bhardlimit = lr_quota_hardlimit >> 10;
    rc = llapi_quotactl(lr_path, qctl);
    WRITELOGMESSAGE(LOG_DEBUG, "=================================================================\n");
    WRITELOGMESSAGE(LOG_DEBUG, "lfs_set_project_quota.lr_path: %s, rc: %d\n", lr_path, rc);
    WRITELOGMESSAGE(LOG_DEBUG, "=================================================================\n");
    if (rc) {
        WRITELOGMESSAGE(LOG_PERROR,
            "lfs_set_project_quota limit: %llu/%llu for project: %u path: %s failed with error: %s" \
                , lr_quota_softlimit, lr_quota_hardlimit, lr_project_id, lr_path, strerror(-rc));
    }
out:
    free(qctl);
    // https://docs.python.org/3/c-api/arg.html
    return Py_BuildValue("i", \
                         rc
                         );

    return result;
}

/* Python3 extension (glue) code 
 * https://docs.python.org/3.6/howto/cporting.html
*/

struct module_state {
    PyObject *error;
};

#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))

static char lfs_docs[] = \
    "Python lustre quota extensions.\n";


static PyMethodDef lfs_funcs[] = {
    {"lfs_set_project_id", (PyCFunction) lfs_set_project_id, METH_VARARGS, "Set lustre project quota id\n"},
    {"lfs_get_project_quota", (PyCFunction) lfs_get_project_quota, METH_VARARGS, "Get lustre project quota\n"},
    {"lfs_set_project_quota", (PyCFunction) lfs_set_project_quota, METH_VARARGS, "Set lustre project quota\n"},
    {NULL}
};

static int lfs_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int lfs_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}


static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        "lustre",
        lfs_docs,
        sizeof(struct module_state),
        lfs_funcs,
        NULL,
        lfs_traverse,
        lfs_clear,
        NULL
};


#define INITERROR return NULL

PyMODINIT_FUNC PyInit_lfs(void) {
    PyObject *module = PyModule_Create(&moduledef);

    if (module == NULL)
        INITERROR;
    struct module_state *st = GETSTATE(module);

    st->error = PyErr_NewException("lustre.Error", NULL, NULL);
    if (st->error == NULL) {
        Py_DECREF(module);
        INITERROR;
    }

    return module;
}