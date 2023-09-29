/*
 * --- BEGIN_HEADER ---
 *
 * libnss_mig - NSS module for MiG user authentication
 * Copyright (C) 2003-2022  The MiG Project lead by Brian Vinter
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
 *
 * -- END_HEADER ---
 *
 * This module is based on libnss-ato which was written by
 * Pietro Donatini <pietro.donatini@unibo.it>.
 *
 * Original copyright notice follows:
 * This product may be distributed under the terms of
 * the GNU Lesser Public License.
 *
 * version 0.1 
 * 
 * ---
 *
 * This MiG version was written by Kenneth Skovhede <skovhede@nbi.ku.dk>,
 * extended for sharelinks+Xsidmount by Jonas Bardino <bardino@nbi.ku.dk>.
 *
 */

/*
 * NSS module for supporting native login of MiG 
 * virtual users. The module checks if a user exists
 * in the MiG system, and maps such a user to the
 * mig-user UID and GID, but with a custom home folder.
 *
 */

#include <nss.h>
#include <pwd.h>
#include <shadow.h>
#include <string.h>
#include <stdio.h>
#include <wordexp.h>
#include <stdlib.h>
#include <unistd.h>
#include <dirent.h>
#include <stdarg.h>
#include <errno.h>
#include <limits.h>

/* Shared helpers for MiG auth */
#include "migauth.h"

/* for security reasons */
#define MIN_UID_NUMBER   500
#define MIN_GID_NUMBER   500
#define CONF_FILE "/etc/libnss_mig.conf"

/* For statically allocated buffers */
#define MAX_USERNAME_LENGTH (1024)
#define PATH_BUF_LEN (2048)

/*
 * the configuration /etc/libnss-mig.conf is a line
 * with the local user data as in /etc/passwd. For example:
 * mig-user:x:1001:1001:P D ,,,:/home/mig/state/user_home/:/bin/sh
 * Extra lines are comments (not processed).
 * The home folder is expected to point to the MiG state folder,
 * where the supplied username will be appended
 * The password is ignored and set to "x" to indicate no password
 */
static struct passwd *read_conf()
{
    FILE *fd;
    struct passwd *conf;

    if ((fd = fopen(CONF_FILE, "r")) == NULL) {
        WRITELOGMESSAGE(LOG_ERR, "Failed to load file %s\n", CONF_FILE);
        return NULL;
    }

    conf = fgetpwent(fd);

    if (conf == NULL) {
        WRITELOGMESSAGE(LOG_ERR, "Failed to parse file %s, error: %d\n",
                        CONF_FILE, errno);
        fclose(fd);
        return NULL;
    }

    if (conf->pw_uid < MIN_UID_NUMBER) {
        WRITELOGMESSAGE(LOG_WARNING, "UID was %d adjusting to %d\n",
                        conf->pw_uid, MIN_UID_NUMBER);
        conf->pw_uid = MIN_UID_NUMBER;
    }

    if (conf->pw_gid < MIN_GID_NUMBER) {
        WRITELOGMESSAGE(LOG_WARNING, "GID was %d adjusting to %d\n",
                        conf->pw_gid, MIN_GID_NUMBER);
        conf->pw_gid = MIN_GID_NUMBER;
    }

    fclose(fd);
    return conf;
}

/* 
 * Allocate some space from the nss static buffer.  The buffer and buflen
 * are the pointers passed in by the C library to the _nss_ntdom_*
 * functions. 
 *
 *  Taken from glibc 
 */

static char *get_static(char **buffer, size_t * buflen, size_t len)
{
    char *result;

    /* Error check.  We return false if things aren't set up right, or
     * there isn't enough buffer space left. */

    if ((buffer == NULL) || (buflen == NULL) || (*buflen > INT_MAX) || (*buflen < len)) {
        return NULL;
    }

    /* Return an index into the static buffer */

    result = *buffer;
    *buffer += len;
    *buflen -= len;

    return result;
}

enum nss_status
_nss_mig_getpwnam_r(const char *name,
                    struct passwd *p, char *buffer, size_t buflen, int *errnop)
{
    struct passwd *conf;
    size_t name_len = strlen(name);

    /* Since we rely on mapping the username to a path on disk,
       double check that the name does not contain path traversal attempts
       after basic input validation */
    if (validate_username(name) != 0 || strstr(name, "..") != NULL
        || strstr(name, "/") != NULL || strstr(name, ":") != NULL) {
        WRITELOGMESSAGE(LOG_INFO, "Invalid username: %s\n", name);
        return NSS_STATUS_NOTFOUND;
    }

    if ((conf = read_conf()) == NULL) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "Invalid config file, username = %s\n", name);
        return NSS_STATUS_NOTFOUND;
    }

    char pathbuf[PATH_BUF_LEN];
    size_t pathlen = strlen(conf->pw_dir);
    int is_share = 0, is_job = 0, is_jupyter = 0;
    /* IMPORTANT: pathbuf is reused so we must quit as soon as login method is
       identified to be sharelink, job or jupyter session to avoid truncating.
     */
    int keep_trying = 1;

#ifdef ENABLE_SHARELINK
    /* Optional anonymous share link access:
       - username must have fixed length matching get_sharelink_length()
       - get_sharelink_home()/SHARELINK_SUBDIR/username must exist as a symlink
       - username and password must be identical or pub key fit authorized_keys
     */
    if (keep_trying && name_len == get_sharelink_length()) {
        WRITELOGMESSAGE(LOG_DEBUG, "Checking for sharelink: %s\n", name);
        memset(pathbuf, 0, PATH_BUF_LEN);
        if (PATH_BUF_LEN ==
            snprintf(pathbuf, PATH_BUF_LEN, "%s/%s/%s",
                     get_sharelink_home(), SHARELINK_SUBDIR, name)) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "Path construction overflow for: %s/%s/%s\n",
                            get_sharelink_home(), SHARELINK_SUBDIR, name);
            return NSS_STATUS_NOTFOUND;
        }
        /* Make sure prefix of direct sharelink target is user home */
        WRITELOGMESSAGE(LOG_DEBUG,
                        "Checking prefix for sharelink: %s\n", pathbuf);
        char link_target[PATH_BUF_LEN];
        memset(link_target, 0, PATH_BUF_LEN);
        if (PATH_BUF_LEN ==
            readlink(pathbuf, link_target, strlen(conf->pw_dir))) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "Link lookup overflow for sharelink: %s\n",
                            pathbuf);
            return NSS_STATUS_NOTFOUND;
        }
        /* Explicitly terminate string after target prefix */
        link_target[strlen(conf->pw_dir)] = 0;
        if (strlen(link_target) == 0) {
            WRITELOGMESSAGE(LOG_DEBUG, "Not a valid sharelink: %s\n", pathbuf);
        } else if (strcmp(conf->pw_dir, link_target) != 0) {
            WRITELOGMESSAGE(LOG_DEBUG,
                            "Not a valid sharelink target prefix: %s\n",
                            link_target);
        } else if (access(link_target, R_OK) != 0) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "Read access to sharelink target %s denied: %s\n",
                            link_target, strerror(errno));
        } else {
            /* Once here it has to be a sharelink - don't try other methods */
            keep_trying = 0;
            /* Match - override home path with sharelink base */
            is_share = 1;
            pathlen =
                strlen(get_sharelink_home()) +
                strlen(SHARELINK_SUBDIR) + name_len + 2;
        }
    }
    WRITELOGMESSAGE(LOG_DEBUG, "Detect sharelink: %d\n", is_share);
#endif                          /* ENABLE_SHARELINK */

#ifdef ENABLE_JOBSIDMOUNT
    /* Optional job session mount access:
       - username must have fixed length matching get_jobsidmount_length()
       - get_jobsidmount_home()/username must exist as a symlink
       - session ssh key must match for access
     */
    if (keep_trying && name_len == get_jobsidmount_length()) {
        WRITELOGMESSAGE(LOG_DEBUG, "Checking for jobsidmount: %s\n", name);
        memset(pathbuf, 0, PATH_BUF_LEN);
        if (PATH_BUF_LEN ==
            snprintf(pathbuf, PATH_BUF_LEN, "%s/%s",
                     get_jobsidmount_home(), name)) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "Path construction overflow for: %s/%s\n",
                            get_jobsidmount_home(), name);
            return NSS_STATUS_NOTFOUND;
        }
        /* Make sure prefix of direct jobsidmount target is user home */
        WRITELOGMESSAGE(LOG_DEBUG,
                        "Checking prefix for jobsidmount: %s\n", pathbuf);
        char link_target[PATH_BUF_LEN];
        memset(link_target, 0, PATH_BUF_LEN);
        if (PATH_BUF_LEN ==
            readlink(pathbuf, link_target, strlen(conf->pw_dir))) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "Link lookup overflow for jobsidmount: %s\n",
                            pathbuf);
            return NSS_STATUS_NOTFOUND;
        }
        /* Explicitly terminate string after target prefix */
        link_target[strlen(conf->pw_dir)] = 0;
        if (strlen(link_target) == 0) {
            WRITELOGMESSAGE(LOG_DEBUG,
                            "Not a valid jobsidmount: %s\n", pathbuf);
        } else if (strcmp(conf->pw_dir, link_target) != 0) {
            WRITELOGMESSAGE(LOG_DEBUG,
                            "Not a valid jobsidmount target prefix: %s\n",
                            link_target);
        } else if (access(link_target, R_OK) != 0) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "Read access to jobsidmount target %s denied: %s\n",
                            link_target, strerror(errno));
        } else {
            /* Once here it has to be a job link - don't try other methods */
            keep_trying = 0;
            /* Match - override home path with jobsidmount base */
            is_job = 1;
            pathlen = strlen(get_jobsidmount_home()) + name_len + 1;
        }
    }
    WRITELOGMESSAGE(LOG_DEBUG, "Detect jobsidmount: %d\n", is_job);
#endif                          /* ENABLE_JOBSIDMOUNT */

#ifdef ENABLE_JUPYTERSIDMOUNT
    /* Optional jupyter session mount access:
       - username must have fixed length matching get_jupytersidmount_length()
       - get_jupytersidmount_home()/username must exist as a symlink
       - session ssh key must match for access
     */
    if (keep_trying && name_len == get_jupytersidmount_length()) {
        WRITELOGMESSAGE(LOG_DEBUG, "Checking for jupytersidmount: %s\n", name);
        memset(pathbuf, 0, PATH_BUF_LEN);
        if (PATH_BUF_LEN ==
            snprintf(pathbuf, PATH_BUF_LEN, "%s/%s",
                     get_jupytersidmount_home(), name)) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "Path construction overflow for: %s/%s\n",
                            get_jupytersidmount_home(), name);
            return NSS_STATUS_NOTFOUND;
        }
        /* Make sure prefix of direct jupytersidmount target is user home */
        WRITELOGMESSAGE(LOG_DEBUG,
                        "Checking prefix for jupytersidmount: %s\n", pathbuf);
        char link_target[PATH_BUF_LEN];
        memset(link_target, 0, PATH_BUF_LEN);
        if (PATH_BUF_LEN ==
            readlink(pathbuf, link_target, strlen(conf->pw_dir))) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "Link lookup overflow for jupytersidmount: %s\n",
                            pathbuf);
            return NSS_STATUS_NOTFOUND;
        }
        /* Explicitly terminate string after target prefix */
        link_target[strlen(conf->pw_dir)] = 0;
        if (strlen(link_target) == 0) {
            WRITELOGMESSAGE(LOG_DEBUG,
                            "Not a valid jupytersidmount: %s\n", pathbuf);
        } else if (strcmp(conf->pw_dir, link_target) != 0) {
            WRITELOGMESSAGE(LOG_DEBUG,
                            "Not a valid jupytersidmount target prefix: %s\n",
                            link_target);
        } else if (access(link_target, R_OK) != 0) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "Read access to jupytersidmount target %s denied: %s\n",
                            link_target, strerror(errno));
        } else {
            /* Once here it has to be a jupyter link - don't try other methods */
            keep_trying = 0;
            /* Match - override home path with jupytersidmount base */
            is_jupyter = 1;
            pathlen = strlen(get_jupytersidmount_home()) + name_len + 1;
        }
    }
    WRITELOGMESSAGE(LOG_DEBUG, "Detect jupytersidmount: %d\n", is_jupyter);
#endif                          /* ENABLE_JUPYTERSIDMOUNT */

    /* Make sure we can fit the path into the buffer */
    if (pathlen + name_len + 2 > PATH_BUF_LEN) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "Expanded path too long, %zd vs %d\n",
                        pathlen + name_len + 2, PATH_BUF_LEN);
        return NSS_STATUS_NOTFOUND;
    }

    /* Build the full path */
    if (is_share == 0 && is_job == 0 && is_jupyter == 0) {
        strcpy(pathbuf, conf->pw_dir);
        if (pathbuf[pathlen] != '/') {
            pathbuf[pathlen] = '/';
            pathbuf[pathlen + 1] = 0;
            pathlen++;
        }
        strcpy(pathbuf + pathlen, name);
    }

    /* Do resolution to remove any weirdness and symlinks */
    char *resolved_path = realpath(pathbuf, NULL);
    if (resolved_path == NULL) {
        WRITELOGMESSAGE(LOG_INFO,
                        "Failed to resolve path to a real path: %s\n", pathbuf);
        return NSS_STATUS_NOTFOUND;
    }

    /* Copy the path back to the statically 
     * allocated buffer to avoid leaking the pointer later */
    pathlen = strlen(resolved_path);
    if (pathlen >= PATH_BUF_LEN) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "Resolved path too long: %zd, %d: %s\n",
                        pathlen, PATH_BUF_LEN, resolved_path);
        free(resolved_path);
        resolved_path = NULL;
        return NSS_STATUS_NOTFOUND;
    }

    /* Check if the folder actually exists */
    DIR *homedir = opendir(resolved_path);
    if (homedir) {
        closedir(homedir);
        /* Copy path into statically allocated buffer 
           so we can free the temporary buffer */
        strcpy(pathbuf, resolved_path);
        free(resolved_path);
        resolved_path = NULL;
    } else {
        WRITELOGMESSAGE(LOG_INFO,
                        "Resolved path is not a directory: %s\n",
                        resolved_path);
        free(resolved_path);
        resolved_path = NULL;
        return NSS_STATUS_NOTFOUND;
    }

    /* All good, user is found, setup result pointer */
    *p = *conf;

    /* If out of memory */
    if ((p->pw_name = get_static(&buffer, &buflen, name_len + 1)) == NULL) {
        return NSS_STATUS_TRYAGAIN;
    }

    /* pw_name stay as the name given */
    strcpy(p->pw_name, name);

    if ((p->pw_passwd = get_static(&buffer, &buflen, strlen("x") + 1)) == NULL) {
        return NSS_STATUS_TRYAGAIN;
    }

    /* "x" is an indicator that the password is in the shadow file */
    strcpy(p->pw_passwd, "x");

    if ((p->pw_dir = get_static(&buffer, &buflen, pathlen + 1)) == NULL) {
        return NSS_STATUS_TRYAGAIN;
    }

    strcpy(p->pw_dir, pathbuf);

    WRITELOGMESSAGE(LOG_DEBUG, "Returning success for %s: %s\n",
                    p->pw_name, p->pw_dir);
    return NSS_STATUS_SUCCESS;
}

enum nss_status
_nss_mig_getspnam_r(const char *name,
                    struct spwd *s, char *buffer, size_t buflen, int *errnop)
{

    /* If out of memory */
    if ((s->sp_namp = get_static(&buffer, &buflen, strlen(name) + 1)) == NULL) {
        return NSS_STATUS_TRYAGAIN;
    }

    strcpy(s->sp_namp, name);

    if ((s->sp_pwdp = get_static(&buffer, &buflen, strlen("*") + 1)) == NULL) {
        return NSS_STATUS_TRYAGAIN;
    }

    /* Set the password as invalid */
    strcpy(s->sp_pwdp, "*");

    s->sp_lstchg = 13571;
    s->sp_min = 0;
    s->sp_max = 99999;
    s->sp_warn = 7;

    return NSS_STATUS_SUCCESS;
}
