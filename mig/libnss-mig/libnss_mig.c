/*
 * --- BEGIN_HEADER ---
 *
 * libnss_mig - NSS module for MiG user authentication
 * Copyright (C) 2003-2017  The MiG Project lead by Brian Vinter
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
 * This MiG version was written by Kenneth Skovhede <skovhede@nbi.ku.dk>
 * and extended for sharelinks by Jonas Bardino <bardino@nb.ku.dk>.
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
#include <syslog.h>
#include <errno.h>
#include <regex.h>
/* TODO: enable conf parsing with this:
#include <ini_config.h>
*/

/* for security reasons */
#define MIN_UID_NUMBER   500
#define MIN_GID_NUMBER   500
#define CONF_FILE "/etc/libnss_mig.conf"

/* Various settings used for username input validation */
/* Something similar to most UN*X account name restrictions */
#ifndef USERNAME_REGEX
/* Default fall-back value used unless given */
/* NOTE: line anchors are mandatory to avoid false hits */
#define USERNAME_REGEX "^[a-z][a-z0-9_-]{0,64}$"
#endif
#ifndef USERNAME_MIN_LENGTH
/* Default fall-back value used unless given */
#define USERNAME_MIN_LENGTH 1
#endif
#ifndef USERNAME_MAX_LENGTH
/* Default fall-back value used unless given */
#define USERNAME_MAX_LENGTH 128
#endif

/* Various settings used by optional sharelink access */
/* Enable sharelinks unless explicitly disabled during compilation */
#ifndef DISABLE_SHARELINK
#define ENABLE_SHARELINK 1
/* Default fall-back values used unless given */
#ifndef SHARELINK_HOME
#define SHARELINK_HOME "/tmp"
#endif
#ifndef SHARELINK_LENGTH
#define SHARELINK_LENGTH 42
#endif
#ifndef SHARELINK_SUBDIR
#define SHARELINK_SUBDIR "read-write"
#endif
#endif				/* !DISABLE_SHARELINK */

/* For statically allocated buffers */
#define MAX_USERNAME_LENGTH (1024)
#define PATH_BUF_LEN (2048)

/* Flag to filter out debug messages */
//#define DEBUG 1

/* Helper function that writes messages to syslog */
static void writelogmessage(int priority, const char *msg, ...)
{
    va_list args;

#ifndef DEBUG
    if (priority == LOG_DEBUG) {
	return;
    }
#endif				/* DEBUG */
    openlog("libnss_mig", LOG_PID, LOG_AUTHPRIV);
    va_start(args, msg);
    vsyslog(priority, msg, args);
    va_end(args);
}

/*
 * the configuration /etc/libnss-mig.conf is a line
 * with the local user data as in /etc/passwd. For example:
 * mig-user:x:1001:1001:P D ,,,:/home/mig/state/user_home/:/bin/bash
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
	writelogmessage(LOG_ERR, "Failed to load file %s\n", CONF_FILE);
	return NULL;
    }

    conf = fgetpwent(fd);

    if (conf == NULL) {
	writelogmessage(LOG_ERR, "Failed to load file %s, error: %d\n",
			CONF_FILE, errno);
	fclose(fd);
	return NULL;
    }

    if (conf->pw_uid < MIN_UID_NUMBER) {
	writelogmessage(LOG_WARNING, "UID was %d adjusting to %d\n",
			conf->pw_uid, MIN_UID_NUMBER);
	conf->pw_uid = MIN_UID_NUMBER;
    }

    if (conf->pw_gid < MIN_GID_NUMBER) {
	writelogmessage(LOG_WARNING, "GID was %d adjusting to %d\n",
			conf->pw_gid, MIN_GID_NUMBER);
	conf->pw_gid = MIN_GID_NUMBER;
    }

    fclose(fd);
    return conf;
}

/* We take first occurence of USERNAME_REGEX from
 * 1. USERNAME_REGEX environment
 * 2. SITE->username_regex (.ini) configuration file
 * 3. USERNAME_REGEX compile time values
 * 4. hard-coded defaults here
 */
static const char *get_username_regex()
{
#ifdef _GNU_SOURCE
    char *username_regex = secure_getenv("USERNAME_REGEX");
#else
    char *username_regex = getenv("USERNAME_REGEX");
#endif
    /* TODO: actually implement option (2):
       if (username_regex == NULL) {
       #ifdef _GNU_SOURCE
       char *conf_path = secure_getenv("MIG_CONF");
       #else
       char *conf_path = getenv("MIG_CONF");
       #endif

       username_regex = conf->username_regex;
       }
     */
    /* Fall back to defined value */
    if (username_regex == NULL) {
	username_regex = USERNAME_REGEX;
    }
    writelogmessage(LOG_DEBUG, "Found username regex %s\n",
		    username_regex);
    return username_regex;
}

/* We take first occurence of sharelink_home and sharelink_length from
 * 1. SHARELINK_HOME and SHARELINK_LENGTH environment
 * 2. sharelink_home and SITE->sharelink_length in (.ini) configuration file
 * 3. SHARELINK_HOME and SHARELINK_LENGTH compile time values
 * 4. hard-coded defaults here
 */
static const char *get_sharelink_home()
{
#ifdef _GNU_SOURCE
    char *sharelink_home = secure_getenv("SHARELINK_HOME");
#else
    char *sharelink_home = getenv("SHARELINK_HOME");
#endif

    /* TODO: actually implement option (2):
       if (sharelink_home == NULL) {
       #ifdef _GNU_SOURCE
       char *conf_path = secure_getenv("MIG_CONF");
       #else
       char *conf_path = getenv("MIG_CONF");
       #endif

       sharelink_home = conf->sharelink_home;
       }
     */
    /* Fall back to defined value */
    if (sharelink_home == NULL) {
	sharelink_home = SHARELINK_HOME;
    }
    writelogmessage(LOG_DEBUG, "Found sharelink home %s\n",
		    sharelink_home);
    return sharelink_home;
}

static const int get_sharelink_length()
{
#ifdef _GNU_SOURCE
    char *sharelink_length = secure_getenv("SHARELINK_LENGTH");
#else
    char *sharelink_length = getenv("SHARELINK_LENGTH");
#endif
    /* TODO: actually implement option (2):
       if (sharelink_length == NULL) {
       #ifdef _GNU_SOURCE
       char *conf_path = secure_getenv("MIG_CONF");
       #else
       char *conf_path = getenv("MIG_CONF");
       #endif
       sharelink_length = conf->sharelink_length;
       }
     */
    if (sharelink_length == NULL) {
	writelogmessage(LOG_DEBUG, "Found sharelink length: %d\n",
			SHARELINK_LENGTH);
	return SHARELINK_LENGTH;
    }
    writelogmessage(LOG_DEBUG, "Found sharelink length %s\n",
		    sharelink_length);
    return atoi(sharelink_length);
}

/* username input validation using username_regex and length helpers */
static int validate_username(const char *username)
{
    writelogmessage(LOG_DEBUG, "Validate username '%s'\n", username);
    if (strlen(username) < USERNAME_MIN_LENGTH) {
	return 1;
    } else if (strlen(username) > USERNAME_MAX_LENGTH) {
	return 2;
    }

    writelogmessage(LOG_DEBUG, "Validated length of username '%s'\n",
		    username);
    int retval;
    regex_t validator;
    int regex_res;
    const char *username_regex = get_username_regex();
    if (strlen(username_regex) < 2 || username_regex[0] != '^' ||
	username_regex[strlen(username_regex) - 1] != '$') {
	/* regex must have begin and end markers to avoid false hits */
	writelogmessage(LOG_ERR,
			"Invalid username regex %s - line anchors required\n",
			username_regex);
	return 3;

    }

    regex_res =
	regcomp(&validator, username_regex, REG_EXTENDED | REG_NOSUB);
    if (regex_res) {
	if (regex_res == REG_ESPACE) {
	    writelogmessage(LOG_ERR,
			    "Memory error in username validation: %s\n",
			    strerror(ENOMEM));
	    retval = 4;
	} else {
	    writelogmessage(LOG_WARNING,
			    "Syntax error in username_regex: %s\n",
			    username_regex);
	    retval = 5;
	}
	return retval;
    }
    writelogmessage(LOG_DEBUG, "Validate username '%s' vs regex '%s'\n",
		    username, username_regex);
    /* Do not try to do submatch on group (last three arguments) */
    regex_res = regexec(&validator, username, 0, NULL, 0);
    if (regex_res == 0) {
	/* Success - username matches regex and length limits */
	writelogmessage(LOG_DEBUG,
			"Validated username '%s' vs regex '%s'\n",
			username, username_regex);
	retval = 0;
    } else if (regex_res == REG_NOMATCH) {
	writelogmessage(LOG_WARNING,
			"username %s did not match username_regex %s\n",
			username, username_regex);
	retval = 6;
    } else {
	writelogmessage(LOG_ERR,
			"Error in regexec: %s\n",
			regerror(regex_res, &validator, NULL, 0));
	retval = 7;
    }
    regfree(&validator);
    writelogmessage(LOG_DEBUG, "Validate username %s returning %d\n",
		    username, retval);
    return retval;
}

/* 
 * Allocate some space from the nss static buffer.  The buffer and buflen
 * are the pointers passed in by the C library to the _nss_ntdom_*
 * functions. 
 *
 *  Taken from glibc 
 */

static char *get_static(char **buffer, size_t * buflen, int len)
{
    char *result;

    /* Error check.  We return false if things aren't set up right, or
     * there isn't enough buffer space left. */

    if ((buffer == NULL) || (buflen == NULL) || (*buflen < len)) {
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
		    struct passwd *p,
		    char *buffer, size_t buflen, int *errnop)
{
    struct passwd *conf;
    size_t name_len = strlen(name);

    /* Since we rely on mapping the username to a path on disk,
       make sure the name does not contain strange things */
    if (validate_username(name) != 0 || strstr(name, "..") != NULL
	|| strstr(name, "/") != NULL || strstr(name, ":") != NULL) {
	writelogmessage(LOG_WARNING, "Invalid username (%d): %s\n",
			name_len, name);
	return NSS_STATUS_NOTFOUND;
    }

    if ((conf = read_conf()) == NULL) {
	writelogmessage(LOG_WARNING,
			"Invalid config file, username = %s\n", name);
	return NSS_STATUS_NOTFOUND;
    }

    char pathbuf[PATH_BUF_LEN];
    size_t pathlen = strlen(conf->pw_dir);
    int is_share = 0;

#ifdef ENABLE_SHARELINK
    /* Optional anonymous share link access:
       - username must have fixed length matching get_sharelink_length()
       - get_sharelink_home()/SHARELINK_SUBDIR/username must exist as a symlink
       - username and password must be identical
     */
    writelogmessage(LOG_DEBUG, "Checking for sharelink: %s\n", name);
    if (strlen(name) == get_sharelink_length()) {
	if (PATH_BUF_LEN ==
	    snprintf(pathbuf, PATH_BUF_LEN, "%s/%s/%s",
		     get_sharelink_home(), SHARELINK_SUBDIR, name)) {
	    writelogmessage(LOG_WARNING,
			    "Path construction failed for: %s/%s/%s\n",
			    get_sharelink_home(), SHARELINK_SUBDIR, name);
	    return NSS_STATUS_NOTFOUND;
	}
	/* Make sure prefix of direct sharelink target is user home */
	writelogmessage(LOG_DEBUG, "Checking prefix for sharelink: %s\n",
			pathbuf);
	char link_target[PATH_BUF_LEN];
	if (PATH_BUF_LEN ==
	    readlink(pathbuf, link_target, strlen(conf->pw_dir))) {
	    writelogmessage(LOG_WARNING,
			    "Link lookup failed for: %s\n", pathbuf);
	    return NSS_STATUS_NOTFOUND;
	}
	/* Explicitly terminate string after target prefix */
	link_target[strlen(conf->pw_dir)] = 0;
	if (strcmp(conf->pw_dir, link_target) != 0) {
	    writelogmessage(LOG_WARNING,
			    "Invalid sharelink target prefix: %s\n",
			    link_target);
	    return NSS_STATUS_NOTFOUND;
	}
	if (access(link_target, R_OK) != 0) {
	    writelogmessage(LOG_WARNING,
			    "Read access to sharelink target %s denied: %s\n",
			    link_target, strerror(errno));
	    return NSS_STATUS_NOTFOUND;
	}
	/* Match - override home path with sharelink base */
	is_share = 1;
	pathlen = strlen(get_sharelink_home()) + strlen(SHARELINK_SUBDIR) +
	    strlen(name) + 2;
    }
    writelogmessage(LOG_DEBUG, "Detect sharelink: %d\n", is_share);
#endif				/* ENABLE_SHARELINK */

    /* Make sure we can fit the path into the buffer */
    if (pathlen + name_len + 2 > PATH_BUF_LEN) {
	writelogmessage(LOG_WARNING, "Expanded path too long, %d vs %d\n",
			pathlen + name_len + 2, PATH_BUF_LEN);
	return NSS_STATUS_NOTFOUND;
    }

    /* Build the full path */
    if (is_share == 0) {
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
	writelogmessage(LOG_WARNING,
			"Failed to resolve path to a real path: %s\n",
			pathbuf);
	return NSS_STATUS_NOTFOUND;
    }

    /* Copy the path back to the statically 
     * allocated buffer to avoid leaking the pointer later */
    pathlen = strlen(resolved_path);
    if (pathlen >= PATH_BUF_LEN) {
	writelogmessage(LOG_WARNING,
			"Resolved path too long: %d, %d: %s\n", pathlen,
			PATH_BUF_LEN, resolved_path);
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
	writelogmessage(LOG_WARNING,
			"Resolved path is not a directory: %s\n",
			resolved_path);
	free(resolved_path);
	resolved_path = NULL;
	return NSS_STATUS_NOTFOUND;
    }

    /* All good, user is found, setup result pointer */
    *p = *conf;

    /* If out of memory */
    if ((p->pw_name =
	 get_static(&buffer, &buflen, strlen(name) + 1)) == NULL) {
	return NSS_STATUS_TRYAGAIN;
    }

    /* pw_name stay as the name given */
    strcpy(p->pw_name, name);

    if ((p->pw_passwd =
	 get_static(&buffer, &buflen, strlen("x") + 1)) == NULL) {
	return NSS_STATUS_TRYAGAIN;
    }

    /* "x" is an indicator that the password is in the shadow file */
    strcpy(p->pw_passwd, "x");

    if ((p->pw_dir = get_static(&buffer, &buflen, pathlen + 1)) == NULL) {
	return NSS_STATUS_TRYAGAIN;
    }

    strcpy(p->pw_dir, pathbuf);

    writelogmessage(LOG_DEBUG, "Returning success for %s: %s\n",
		    p->pw_name, p->pw_dir);
    return NSS_STATUS_SUCCESS;
}

enum nss_status
_nss_mig_getspnam_r(const char *name,
		    struct spwd *s,
		    char *buffer, size_t buflen, int *errnop)
{

    /* If out of memory */
    if ((s->sp_namp =
	 get_static(&buffer, &buflen, strlen(name) + 1)) == NULL) {
	return NSS_STATUS_TRYAGAIN;
    }

    strcpy(s->sp_namp, name);

    if ((s->sp_pwdp =
	 get_static(&buffer, &buflen, strlen("*") + 1)) == NULL) {
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
