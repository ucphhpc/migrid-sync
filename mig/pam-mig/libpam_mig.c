/*
 * libpam_mig - PAM module for MiG user authentication
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
 */

/*
 * PAM module for supporting native login of MiG 
 * virtual users. The module checks if a user exists
 * in the MiG system, and maps such a user to the
 * mig-user UID and GID, but with a custom home folder.
 *
 * Written by Kenneth Skovhede <skovhede@nbi.ku.dk>
 * Extended for sharelinks by Jonas Bardino <bardino@nb.ku.dk>
 *
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <regex.h>

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdarg.h>
#include <pwd.h>
#include <syslog.h>

#include <security/pam_appl.h>
#include <security/pam_modules.h>

/* TODO: enable conf parsing with this:
#include <ini_config.h>
*/

#define PASSWORD_FILENAME "authorized_passwords"

/* Various settings used to communicate chrooting */
//#define ENABLE_CHROOT 1

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

/* Setup for communicating between layers */
#define PAM_DATA_NAME "MIG_DO_CHROOT"
#define PAM_CHROOT_AUTHENTICATED ((void*)1)
#define PAM_CHROOT_REQUEST ((void*)2)
#define PAM_CHROOT_COMPLETED ((void*)3)

/* For service to dot-dir lookup */
#define SSHD_SERVICE "sshd"
#define SSHD_AUTH_DIR "ssh"
#define FTPD_SERVICE "ftpd"
#define FTPD_AUTH_DIR "ftps"
#define WEBDAVS_SERVICE "webdavs"
#define WEBDAVS_AUTH_DIR "davs"

/* For testing, the printf can be activated,
   but should never be enabled in non-debug mode */
//#define DEBUG_PRINTF 1
/* Print debug messages as well */
#define DEBUG 1

/* The sizes here are use to handle static
   allocations of buffers */
#define MAX_DIGEST_SIZE (2048)
#define MAX_PATH_LENGTH (2048)

/* Sanity limit to avoid really short and easily guessable
   digest values */
#define MIN_PBKDF_LENGTH (16)

/* Helper function that writes messages to syslog */
static void writelogmessage(int priority, const char *msg, ...)
{
    va_list args;

#ifndef DEBUG
    if (priority == LOG_DEBUG) {
	return;
    }
#endif				/* DEBUG */
    openlog("pam_mig", LOG_PID, LOG_AUTHPRIV);
    va_start(args, msg);
    vsyslog(priority, msg, args);
    va_end(args);

#ifdef DEBUG
#ifdef DEBUG_PRINTF
    va_start(args, msg);
    vprintf(msg, args);
    va_end(args);
#endif				/*DEBUG_PRINTF */
#endif				/* DEBUG */
}

/* Dump the code we depend on here, to prevent linker/loader dependencies */
/*
 * BEWARE: The sha2_* functions in pbkdf2 needs to be declared "static"
 *         otherwise they clash with openssh and segfaults it.
 *         the file has been modified to make these functions static
 */

#include "pbkdf2-sha256.c"
#include "b64-decode.c"
#include "b64.c"

static const char *get_service_dir(const char *service)
{
    if (strcmp(service, SSHD_SERVICE) == 0) {
	return SSHD_AUTH_DIR;
    } else if (strcmp(service, FTPD_SERVICE) == 0) {
	return FTPD_AUTH_DIR;
    } else if (strcmp(service, WEBDAVS_SERVICE) == 0) {
	return WEBDAVS_AUTH_DIR;
    } else {
	return service;
    }
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

/* We take first occurence of SHARELINK_HOME and SHARELINK_LENGTH from
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

/* this function is ripped from pam_unix/support.c, it lets us do IO via PAM */
static int converse(pam_handle_t * pamh, int nargs,
		    struct pam_message **message,
		    struct pam_response **response)
{
    int retval;
    struct pam_conv *conv;

    retval = pam_get_item(pamh, PAM_CONV, (const void **) &conv);
    if (retval == PAM_SUCCESS) {
	retval =
	    conv->conv(nargs, (const struct pam_message **) message,
		       response, conv->appdata_ptr);
    }

    return retval;
}

/* The do_chroot function invokes chroot to force the user into the home directory */
#ifdef ENABLE_CHROOT
static int do_chroot(pam_handle_t * pamh)
{
    int retval;

    const char *pUsername;
    retval = pam_get_user(pamh, &pUsername, "Username: ");

    if (retval != PAM_SUCCESS || pUsername == NULL
	|| strlen(pUsername) == 0) {
	writelogmessage(LOG_WARNING, "Did not get a valid username ...\n");
	if (retval != PAM_SUCCESS) {
	    return retval;
	} else {
	    return PAM_AUTH_ERR;
	}
    }

    /* Since we rely on mapping the username to a path on disk,
       make sure the name does not contain strange things */
    if (strstr(pUsername, "..") != NULL || strstr(pUsername, "/") != NULL
	|| strstr(pUsername, ":") != NULL) {
	writelogmessage(LOG_WARNING,
			"Username did not pass validation: %s\n",
			pUsername);
	return PAM_AUTH_ERR;
    }

    struct passwd *pw = getpwnam(pUsername);
    if (pw == NULL) {
	writelogmessage(LOG_WARNING, "User not found: %s\n", pUsername);
	return PAM_AUTH_ERR;
    }

    if (chdir(pw->pw_dir) != 0) {
	writelogmessage(LOG_WARNING, "Unable to chdir to %s\n",
			pw->pw_dir);
	return PAM_AUTH_ERR;
    }

    writelogmessage(LOG_DEBUG, "Activating chroot for '%s': %s\n",
		    pUsername, pw->pw_dir);
    if (chroot(pw->pw_dir) == 0) {
	writelogmessage(LOG_DEBUG, "Chroot activated (%s)!\n",
			strerror(errno));
	if (chdir("/") != 0) {
	    writelogmessage(LOG_WARNING,
			    "Unable to chdir to / after chroot\n");
	    return PAM_AUTH_ERR;
	} else {
	    writelogmessage(LOG_DEBUG, "Changed into new root!\n");
	}

	writelogmessage(LOG_DEBUG, "Returning success ...\n");
	return PAM_SUCCESS;
    } else {
	writelogmessage(LOG_WARNING, "Chroot failed to activate: %s!\n",
			strerror(errno));
	return PAM_AUTH_ERR;
    }

    return PAM_SUCCESS;
}
#endif				/* ENABLE_CHROOT */

PAM_EXTERN int pam_sm_close_session(pam_handle_t * pamh, int flags,
				    int argc, const char **argv)
{
    writelogmessage(LOG_DEBUG, "pam_sm_close_session: %i, %i\n", flags,
		    argc);
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_open_session(pam_handle_t * pamh, int flags,
				   int argc, const char **argv)
{
    writelogmessage(LOG_DEBUG, "pam_sm_open_session: %i, %i\n", flags,
		    argc);

#ifdef ENABLE_CHROOT
    int retval;

    // TODO: Check if the user is a mig-mapped user,
    // otherwise, do not chroot it

    const void *val;
    retval = pam_get_data(pamh, PAM_DATA_NAME, &val);
    if (retval == PAM_SUCCESS && val == PAM_CHROOT_AUTHENTICATED) {
	retval =
	    pam_set_data(pamh, PAM_DATA_NAME, PAM_CHROOT_REQUEST, NULL);
	if (retval != PAM_SUCCESS) {
	    writelogmessage(LOG_WARNING,
			    "Failed to get set chroot hook\n");
	    return retval;
	} else {
	    writelogmessage(LOG_DEBUG, "Registered for chroot \n");
	}
    }
#endif				/*ENABLE_CHROOT */


    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_chauthtok(pam_handle_t * pamh, int flags, int argc,
				const char **argv)
{
    writelogmessage(LOG_DEBUG, "pam_sm_chauthtok: %i, %i\n", flags, argc);
    return PAM_SUCCESS;
}

/* expected hook */
PAM_EXTERN int pam_sm_setcred(pam_handle_t * pamh, int flags, int argc,
			      const char **argv)
{
    writelogmessage(LOG_DEBUG, "Set cred: %i, %i\n", flags, argc);

#ifdef ENABLE_CHROOT

    int retval;
    const void *val;
    retval = pam_get_data(pamh, PAM_DATA_NAME, &val);
    if (retval == PAM_SUCCESS && val == PAM_CHROOT_REQUEST) {
	retval =
	    pam_set_data(pamh, PAM_DATA_NAME, PAM_CHROOT_COMPLETED, NULL);
	if (retval != PAM_SUCCESS) {
	    writelogmessage(LOG_WARNING,
			    "Failed to get unset chroot hook\n");
	    return retval;
	}
	return do_chroot(pamh);
    }
#endif				/*ENABLE_CHROOT */

    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_acct_mgmt(pam_handle_t * pamh, int flags, int argc,
				const char **argv)
{
    writelogmessage(LOG_DEBUG, "Acct mgmt\n");
    return PAM_SUCCESS;
}

/* expected hook, this is where custom stuff happens */
PAM_EXTERN int pam_sm_authenticate(pam_handle_t * pamh, int flags,
				   int argc, const char **argv)
{
    int retval;

    writelogmessage(LOG_DEBUG, "In pam_sm_authenticate\n");

    const char *pUsername;
    retval = pam_get_user(pamh, &pUsername, "Username: ");

    if (retval != PAM_SUCCESS || pUsername == NULL
	|| strlen(pUsername) == 0) {
	writelogmessage(LOG_WARNING, "Did not get a valid username ...\n");
	if (retval != PAM_SUCCESS) {
	    return retval;
	} else {
	    return PAM_AUTH_ERR;
	}

    }

    /* Since we rely on mapping the username to a path on disk,
       make sure the name does not contain strange things */
    if (validate_username(pUsername) != 0
	|| strstr(pUsername, "..") != NULL
	|| strstr(pUsername, "/") != NULL
	|| strstr(pUsername, ":") != NULL) {
	writelogmessage(LOG_WARNING,
			"Username failed validation checks: %s\n",
			pUsername);
	return PAM_AUTH_ERR;
    }

    writelogmessage(LOG_DEBUG, "Checking pw entry for '%s'\n", pUsername);

    struct passwd *pw = getpwnam(pUsername);
    if (pw == NULL) {
	writelogmessage(LOG_WARNING, "User not found: %s\n", pUsername);
	return PAM_AUTH_ERR;
    }

    const char *pPassword;
    retval = pam_get_item(pamh, PAM_AUTHTOK, (const void **) &pPassword);
    if (retval != PAM_SUCCESS) {
	writelogmessage(LOG_INFO, "Failed to get password token\n");
	return retval;
    }

    if (pPassword == NULL) {
	writelogmessage(LOG_DEBUG, "No password, requesting one ...\n");
	struct pam_message msg[1], *pmsg[1];
	struct pam_response *resp;

	pmsg[0] = &msg[0];
	msg[0].msg_style = PAM_PROMPT_ECHO_OFF;
	msg[0].msg = "Password: ";
	resp = NULL;

	retval = converse(pamh, 1, pmsg, &resp);
	if (retval != PAM_SUCCESS) {
	    writelogmessage(LOG_INFO, "Failed to converse\n");
	    return retval;
	}

	if (resp) {
	    if ((flags & PAM_DISALLOW_NULL_AUTHTOK)
		&& resp[0].resp == NULL) {
		writelogmessage(LOG_INFO, "Failed with nullauth\n");
		free(resp);
		return PAM_AUTH_ERR;
	    }

	    writelogmessage(LOG_DEBUG,
			    "Got user password, checking correctness ...\n");
	    pPassword = resp[0].resp;
	    resp[0].resp = NULL;
	} else {
	    writelogmessage(LOG_INFO, "Failed to converse - 2\n");
	    return PAM_CONV_ERR;
	}
    }

    const char *pService;

    retval = pam_get_item(pamh, PAM_SERVICE, (const void **) &pService);
    if (retval != PAM_SUCCESS) {
	writelogmessage(LOG_WARNING, "Failed to get service name\n");
	return retval;
    }
#ifdef ENABLE_SHARELINK
    /* Optional anonymous share link access:
       - username must have fixed length matching get_sharelink_length()
       - get_sharelink_home()/SHARELINK_SUBDIR/username must exist as a symlink
       - username and password must be identical
     */
    writelogmessage(LOG_DEBUG, "Checking for sharelink: %s\n", pUsername);
    if (strlen(pUsername) == get_sharelink_length()) {
	char share_path[MAX_PATH_LENGTH];
	if (MAX_PATH_LENGTH ==
	    snprintf(share_path, MAX_PATH_LENGTH, "%s/%s/%s",
		     get_sharelink_home(), SHARELINK_SUBDIR, pUsername)) {
	    writelogmessage(LOG_WARNING,
			    "Path construction failed for: %s/%s/%s\n",
			    get_sharelink_home(), SHARELINK_SUBDIR,
			    pUsername);
	    return PAM_AUTH_ERR;
	}
	/* NSS lookup assures sharelink target is valid and inside user home */
	/* Just check simple access here to make sure it is a share link */
	if (access(share_path, R_OK) == 0) {
	    writelogmessage(LOG_DEBUG,
			    "Checking sharelink id %s password\n",
			    pUsername);
	    if (strcmp(pUsername, pPassword) == 0) {
		writelogmessage(LOG_DEBUG, "Return sharelink success\n");
		return PAM_SUCCESS;
	    } else {
		writelogmessage(LOG_WARNING,
				"Username and password mismatch for sharelink: %s\n",
				pUsername);
		return PAM_AUTH_ERR;
	    }
	} else {
	    writelogmessage(LOG_DEBUG,
			    "No matching sharelink: %s. Try user auth.\n",
			    share_path);
	}
    } else {
	writelogmessage(LOG_DEBUG,
			"Not a sharelink username: %s. Try user auth.\n",
			pUsername);
    }
#endif				/* ENABLE_SHARELINK */

    writelogmessage(LOG_DEBUG, "Checking for standard user/password: %s\n",
		    pUsername);
    char auth_filename[MAX_PATH_LENGTH];
    if (MAX_PATH_LENGTH ==
	snprintf(auth_filename, MAX_PATH_LENGTH, "%s/.%s/%s", pw->pw_dir,
		 get_service_dir(pService), PASSWORD_FILENAME)) {
	writelogmessage(LOG_WARNING,
			"Path construction failed for: %s/.%s/%s\n",
			pw->pw_dir, get_service_dir(pService),
			PASSWORD_FILENAME);
	return PAM_AUTH_ERR;
    }

    if (access(auth_filename, R_OK) != 0) {
	writelogmessage(LOG_WARNING, "Read access to file %s denied: %s\n",
			auth_filename, strerror(errno));
	return PAM_AUTH_ERR;
    }

    struct stat st;
    if (stat(auth_filename, &st) != 0) {
	writelogmessage(LOG_WARNING, "Failed to read file size: %s\n",
			auth_filename);
	return PAM_AUTH_ERR;
    }

    if (st.st_size > MAX_DIGEST_SIZE) {
	writelogmessage(LOG_WARNING,
			"pbkdf digest file size was %d but only %d is allowed, filename: %s\n",
			st.st_size, MAX_DIGEST_SIZE, auth_filename);
	return PAM_AUTH_ERR;
    }

    char pbkdf[MAX_DIGEST_SIZE];
    FILE *fd = fopen(auth_filename, "rb");
    if (fd == NULL) {
	writelogmessage(LOG_WARNING,
			"Failed to open file for reading, filename: %s\n",
			auth_filename);
	return PAM_AUTH_ERR;

    }
    if (fread(pbkdf, sizeof(char), st.st_size, fd) != st.st_size) {
	writelogmessage(LOG_WARNING,
			"Failed to read %d bytes from filename: %s\n",
			st.st_size, auth_filename);
	fclose(fd);
	return PAM_AUTH_ERR;
    }
    fclose(fd);

    //fread does not null terminate the string
    pbkdf[st.st_size] = 0;

    writelogmessage(LOG_DEBUG, "read %s (%d) from password file", pbkdf,
		    strlen(pbkdf));

    if (strstr(pbkdf, "PBKDF2$") != pbkdf) {
	writelogmessage(LOG_WARNING,
			"The pbkdf format was incorrect in file %s\n",
			auth_filename);
	return PAM_AUTH_ERR;
    }

    char *pHashAlg = strchr(pbkdf, '$');
    if (pHashAlg == NULL) {
	writelogmessage(LOG_WARNING,
			"The pbkdf hash algorithm was incorrect in %s\n",
			auth_filename);
	return PAM_AUTH_ERR;
    }

    pHashAlg++;

    char *pItCount = strchr(pHashAlg, '$');
    if (pItCount == NULL) {
	writelogmessage(LOG_WARNING,
			"The pbkdf iteration count was incorrect in %s\n",
			auth_filename);
	return PAM_AUTH_ERR;
    }

    *pItCount = 0;
    pItCount++;

    char *pBase64Salt = strchr(pItCount, '$');
    if (pBase64Salt == NULL) {
	writelogmessage(LOG_WARNING,
			"The pbkdf salt was incorrect in %s\n",
			auth_filename);
	return PAM_AUTH_ERR;
    }

    *pBase64Salt = 0;
    pBase64Salt++;

    char *pBase64Hash = strchr(pBase64Salt, '$');
    if (pBase64Hash == NULL) {
	writelogmessage(LOG_WARNING,
			"The pbkdf salt was incorrect in %s\n",
			auth_filename);
	return PAM_AUTH_ERR;
    }

    *pBase64Hash = 0;
    pBase64Hash++;

    long iteration_count = strtol(pItCount, NULL, 10);
    if (iteration_count <= 0) {
	writelogmessage(LOG_WARNING,
			"The pbkdf iteration count was not a correct integer, file: %s\n",
			auth_filename);
	return PAM_AUTH_ERR;
    }

    if (strcmp(pHashAlg, "sha256") != 0) {
	writelogmessage(LOG_WARNING,
			"The hash algorithm should be sha256, but it was %s\n",
			pHashAlg);
	return PAM_AUTH_ERR;
    }

    char pSaltAndHash[MAX_DIGEST_SIZE];

    size_t salt_size = b64_get_decoded_buffer_size(strlen(pBase64Salt));
    size_t hash_size = b64_get_decoded_buffer_size(strlen(pBase64Hash));

    if (hash_size > (256 / 8)) {
	writelogmessage(LOG_WARNING,
			"The hash was size %d, but it should be at most %d for SHA256\n",
			hash_size, 256 / 8);
	return PAM_AUTH_ERR;
    }

    if (hash_size < MIN_PBKDF_LENGTH) {
	writelogmessage(LOG_WARNING,
			"The hash was size %d, but it should be at least %d \n",
			hash_size, MIN_PBKDF_LENGTH);
	return PAM_AUTH_ERR;
    }

    if (salt_size + hash_size > MAX_DIGEST_SIZE) {
	writelogmessage(LOG_WARNING,
			"The expanded salt and hash were too big, reading from file: %s\n",
			auth_filename);
	return PAM_AUTH_ERR;
    }

    if (b64_decode
	((const uint8_t *) pBase64Salt, strlen(pBase64Salt),
	 (uint8_t *) pSaltAndHash) != salt_size) {
	writelogmessage(LOG_WARNING,
			"Failed to base64 decode salt from file: %s\n",
			auth_filename);
	return PAM_AUTH_ERR;
    }
    if (b64_decode
	((const uint8_t *) pBase64Hash, strlen(pBase64Hash),
	 (uint8_t *) pSaltAndHash + salt_size) != hash_size) {
	writelogmessage(LOG_WARNING,
			"Failed to base64 decode hash from file: %s\n",
			auth_filename);
	return PAM_AUTH_ERR;
    }

    writelogmessage(LOG_DEBUG,
		    "Checking password with pbkdf value from %s ...\n",
		    auth_filename);

    char pResult[MAX_DIGEST_SIZE];

    PKCS5_PBKDF2_HMAC((unsigned char *) pPassword,
		      strlen(pPassword),
		      (unsigned char *) pBase64Salt,
		      strlen(pBase64Salt),
		      iteration_count,
		      hash_size, (unsigned char *) pResult);

    size_t expaded_hash_size = b64_get_encoded_buffer_size(hash_size);
    if (expaded_hash_size >= MAX_DIGEST_SIZE) {
	writelogmessage(LOG_WARNING,
			"Failed to base64 encode hash from file: %s\n",
			auth_filename);
	return PAM_AUTH_ERR;
    }

    b64_encode((const uint8_t *) pResult, hash_size, (uint8_t *) & pbkdf);
    //b64 encode does not null terminate the string
    pbkdf[expaded_hash_size] = 0;

    if (strcmp(pBase64Hash, pbkdf) != 0) {
	writelogmessage(LOG_INFO,
			"Supplied password did not match the stored pbkdf digest\n");
	writelogmessage(LOG_DEBUG,
			"Supplied password  \"%s\" did not match the stored pbkdf digest \"%s\"\n",
			pbkdf, pBase64Hash);
	return PAM_AUTH_ERR;
    }
#ifdef ENABLE_CHROOT
    retval =
	pam_set_data(pamh, PAM_DATA_NAME, PAM_CHROOT_AUTHENTICATED, NULL);
    if (retval != PAM_SUCCESS) {
	writelogmessage(LOG_WARNING, "Failed to get set chroot hook\n");
	return retval;
    }
#endif				/*ENABLE_CHROOT */

    writelogmessage(LOG_DEBUG, "Return success\n");
    return PAM_SUCCESS;
}
