/*
 * libpam_mig - PAM module for MiG user authentication
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
 * PAM module for supporting native login of MiG 
 * virtual users. The module checks if a user exists
 * in the MiG system, and maps such a user to the
 * mig-user UID and GID, but with a custom home folder.
 *
 * Written by Kenneth Skovhede <skovhede@nbi.ku.dk>
 * Extended for sharelinks/Xsidmount by Jonas Bardino <bardino@nbi.ku.dk>
 * Extended for MiG python auth handling by Martin Rehr <rehr@nbi.ku.dk>
 *
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <regex.h>

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdarg.h>
#include <pwd.h>

#include <security/pam_appl.h>
#include <security/pam_modules.h>

/* For ip resolve */
#include <netdb.h>
#include <arpa/inet.h>

/* Shared helpers for MiG auth */
#include "migauth.h"

/* Various settings used to communicate chrooting */
//#define ENABLE_CHROOT 1

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

/* Various settings used for password input validation */
#ifndef PASSWORD_MIN_LENGTH
/* Default fall-back value used unless given */
#define PASSWORD_MIN_LENGTH 6
#endif
#ifndef PASSWORD_MAX_LENGTH
/* Default fall-back value used unless given */
#define PASSWORD_MAX_LENGTH 128
#endif
#ifndef PASSWORD_MIN_CLASSES
/* Default fall-back value used unless given */
#define PASSWORD_MIN_CLASSES 2
#endif

/* The sizes here are use to handle static
   allocations of buffers */
#define MAX_DIGEST_SIZE (2048)
#define MAX_PATH_LENGTH (2048)

/* Sanity limit to avoid really short and easily guessable
   digest values */
#define MIN_PBKDF_LENGTH (16)

/* Dump the code we depend on here, to prevent linker/loader dependencies */
/*
 * BEWARE: The sha2_* functions in pbkdf2 needs to be declared "static"
 *         otherwise they clash with openssh and segfaults it.
 *         the file has been modified to make these functions static
 */

#include "pbkdf2-sha256.c"
#include "b64-decode.c"
#include "b64.c"
#ifdef ENABLE_AUTHHANDLER
#include "migauthhandler.c"
#endif

/* Service dot-dir lookup helper */
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

static int get_password_min_length()
{
    return get_runtime_var_int("PASSWORD_MIN_LENGTH",
                   "site->password_min_length",
                   PASSWORD_MIN_LENGTH);
}

static int get_password_min_classes()
{
    return get_runtime_var_int("PASSWORD_MIN_CLASSES",
                   "site->password_min_classes",
                   PASSWORD_MIN_CLASSES);
}

/* password input validation using char class and length helpers */
static int validate_password(const char *password)
{
    /* NOTE: never log raw password */
    WRITELOGMESSAGE(LOG_DEBUG, "Validate password: %s\n", password);
    if (strlen(password) < get_password_min_length()) {
        WRITELOGMESSAGE(LOG_INFO,
                "Invalid password - too short (%zd < %d)\n",
                strlen(password), get_password_min_length());
        return 1;
    } else if (strlen(password) > PASSWORD_MAX_LENGTH) {
        WRITELOGMESSAGE(LOG_INFO,
                "Invalid password - too long (%zd > %d)\n",
                strlen(password), PASSWORD_MAX_LENGTH);
        return 2;
    }

    WRITELOGMESSAGE(LOG_DEBUG, "Validated length of password: %zd\n",
            strlen(password));
    int i;
    int lower = 0, upper = 0, digit = 0, other = 0, classes = 0;
    for (i = 0; i < strlen(password); i++) {
        if (islower(password[i])) {
            lower++;
        } else if (isupper(password[i])) {
            upper++;
        } else if (isdigit(password[i])) {
            digit++;
        } else {
            other++;
        }
    }
    classes = (lower > 0) + (upper > 0) + (digit > 0) + (other > 0);
    if (classes < get_password_min_classes()) {
        WRITELOGMESSAGE(LOG_INFO,
                "password has too few character classes (%d < %d)\n",
                classes, get_password_min_classes());
        return 1;
    }
    /* Success - password matches regex and length limits */
    WRITELOGMESSAGE(LOG_DEBUG,
            "Validated password of length %zd and %d char classes\n",
            strlen(password), classes);
    return 0;
}

/* this function is ripped from pam_unix/support.c, it lets us do IO via PAM */
static int converse(pam_handle_t * pamh, int nargs,
            struct pam_message **message,
            struct pam_response **response)
{
    int retval;
    struct pam_conv *conv;

    retval = pam_get_item(pamh, PAM_CONV, (const void **)&conv);
    if (retval == PAM_SUCCESS) {
        retval =
            conv->conv(nargs, (const struct pam_message **)message,
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
        WRITELOGMESSAGE(LOG_WARNING,
                "Did not get a valid username ...\n");
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
        WRITELOGMESSAGE(LOG_INFO,
                "Username did not pass validation: %s\n",
                pUsername);
        return PAM_AUTH_ERR;
    }

    struct passwd *pw = getpwnam(pUsername);
    if (pw == NULL) {
        WRITELOGMESSAGE(LOG_INFO, "User not found: %s\n", pUsername);

        return PAM_AUTH_ERR;
    }

    if (chdir(pw->pw_dir) != 0) {
        WRITELOGMESSAGE(LOG_WARNING, "Unable to chdir to %s\n",
                pw->pw_dir);
        return PAM_AUTH_ERR;
    }

    WRITELOGMESSAGE(LOG_DEBUG, "Activating chroot for '%s': %s\n",
            pUsername, pw->pw_dir);
    if (chroot(pw->pw_dir) == 0) {
        WRITELOGMESSAGE(LOG_DEBUG, "Chroot activated (%s)!\n",
                strerror(errno));
        if (chdir("/") != 0) {
            WRITELOGMESSAGE(LOG_WARNING,
                    "Unable to chdir to / after chroot\n");
            return PAM_AUTH_ERR;
        } else {
            WRITELOGMESSAGE(LOG_DEBUG, "Changed into new root!\n");
        }

        WRITELOGMESSAGE(LOG_DEBUG, "Returning success ...\n");
        return PAM_SUCCESS;
    } else {
        WRITELOGMESSAGE(LOG_WARNING, "Chroot failed to activate: %s!\n",
                strerror(errno));
        return PAM_AUTH_ERR;
    }

    return PAM_SUCCESS;
}
#endif              /* ENABLE_CHROOT */

PAM_EXTERN int pam_sm_close_session(pam_handle_t * pamh, int flags,
                    int argc, const char **argv)
{
    WRITELOGMESSAGE(LOG_DEBUG, "pam_sm_close_session: %i, %i\n", flags,
            argc);
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_open_session(pam_handle_t * pamh, int flags,
                   int argc, const char **argv)
{
    WRITELOGMESSAGE(LOG_DEBUG, "pam_sm_open_session: %i, %i\n", flags,
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
            WRITELOGMESSAGE(LOG_WARNING,
                    "Failed to get set chroot hook\n");
            return retval;
        } else {
            WRITELOGMESSAGE(LOG_DEBUG, "Registered for chroot \n");
        }
    }
#endif              /* ENABLE_CHROOT */

    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_chauthtok(pam_handle_t * pamh, int flags, int argc,
                const char **argv)
{
    WRITELOGMESSAGE(LOG_DEBUG, "pam_sm_chauthtok: %i, %i\n", flags, argc);
    return PAM_SUCCESS;
}

/* expected hook */
PAM_EXTERN int pam_sm_setcred(pam_handle_t * pamh, int flags, int argc,
                  const char **argv)
{
    WRITELOGMESSAGE(LOG_DEBUG, "Set cred: %i, %i\n", flags, argc);

#ifdef ENABLE_CHROOT

    int retval;
    const void *val;
    retval = pam_get_data(pamh, PAM_DATA_NAME, &val);
    if (retval == PAM_SUCCESS && val == PAM_CHROOT_REQUEST) {
        retval =
            pam_set_data(pamh, PAM_DATA_NAME, PAM_CHROOT_COMPLETED,
                 NULL);
        if (retval != PAM_SUCCESS) {
            WRITELOGMESSAGE(LOG_WARNING,
                    "Failed to get unset chroot hook\n");
            return retval;
        }
        return do_chroot(pamh);
    }
#endif              /* ENABLE_CHROOT */

    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_acct_mgmt(pam_handle_t * pamh, int flags, int argc,
                const char **argv)
{
    WRITELOGMESSAGE(LOG_DEBUG,
            "Acct mgmt: pamh=%p flags=%x, argc=%d, argv:%p\n",
            (void *)pamh, flags, argc, (void *)argv);
    return PAM_SUCCESS;
}

/* expected hook, this is where custom stuff happens */
PAM_EXTERN int pam_sm_authenticate(pam_handle_t * pamh, int flags,
                   int argc, const char **argv)
{
    int retval;
    WRITELOGMESSAGE(LOG_DEBUG,
            "In pam_sm_authenticate: pamh=%p flags=%x, argc=%d, argv:%p\n",
            (void *)pamh, flags, argc, (void *)argv);
#ifdef ENABLE_AUTHHANDLER

    /* Resolve ip address */

    const char *pHostname;
    const char *pAddress;
    struct hostent *he;
    struct in_addr **addr_list;

    retval = pam_get_item(pamh, PAM_RHOST, (const void **)&pHostname);
    if (retval != PAM_SUCCESS || pHostname == NULL
        || strlen(pHostname) == 0) {
        WRITELOGMESSAGE(LOG_ERR, "Unable to resolve remote host ...\n");
        return PAM_AUTH_ERR;
    }
    if ((he = gethostbyname(pHostname)) == NULL) {
        WRITELOGMESSAGE(LOG_ERR,
                "Unable to resolve address from host: %s\n",
                pHostname);
        return PAM_AUTH_ERR;
    }
    addr_list = (struct in_addr **)he->h_addr_list;
    if (addr_list[0] == NULL) {
        WRITELOGMESSAGE(LOG_ERR,
                "Unable to resolve address from host: %s\n",
                pHostname);
        return PAM_AUTH_ERR;
    }
    pAddress = inet_ntoa(*addr_list[0]);
    WRITELOGMESSAGE(LOG_DEBUG,
            "Resolved remote address: %s from host: %s\n", pAddress,
            pHostname);
#endif              /* ENABLE_AUTHHANDLER */

    /* Check PAM user */

    const char *pUsername;
    retval = pam_get_user(pamh, &pUsername, "Username: ");
    if (retval != PAM_SUCCESS || pUsername == NULL
        || strlen(pUsername) == 0) {
        WRITELOGMESSAGE(LOG_WARNING,
                "Did not get a valid username ...\n");
#ifdef ENABLE_AUTHHANDLER
        register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                      | MIG_AUTHTYPE_PASSWORD
                      | MIG_INVALID_USERNAME,
                      pUsername, pAddress, NULL);
#endif              /* ENABLE_AUTHHANDLER */
        if (retval != PAM_SUCCESS) {
            return retval;
        } else {
            return PAM_AUTH_ERR;
        }
    }
#ifdef ENABLE_AUTHHANDLER

    /* Check MiG ratelimit */

    int rate_limit_expired = mig_expire_rate_limit();
    WRITELOGMESSAGE(LOG_DEBUG, "rate_limit_expired: %d\n",
            rate_limit_expired);
    bool exceeded_rate_limit = mig_hit_rate_limit(pUsername, pAddress);
    WRITELOGMESSAGE(LOG_DEBUG, "exceeded_rate_limit: %d\n",
            exceeded_rate_limit);
    if (exceeded_rate_limit == true) {
        register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                      | MIG_AUTHTYPE_PASSWORD
                      | MIG_EXCEEDED_RATE_LIMIT,
                      pUsername, pAddress, NULL);
        return PAM_AUTH_ERR;
    }

    /* check MiG max sftp sessions */
    
    /* NOTE: Disabled for now, 
     * this require session open/close tracking in sftp_subsys.py 

    bool exceeded_max_sessions = mig_exceeded_max_sessions(pUsername,
                                                        pAddress);
    WRITELOGMESSAGE(LOG_DEBUG, "exceeded_max_sessions: %d\n",
            exceeded_max_sessions);
    if (exceeded_max_sessions == true) {
        register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                      | MIG_AUTHTYPE_PASSWORD
                      | MIG_EXCEEDED_MAX_SESSIONS,
                      pUsername, pAddress, NULL);
        return PAM_AUTH_ERR;
    }
    */
#endif              /* ENABLE_AUTHHANDLER */

    /* Validate username */

    /* Since we rely on mapping the username to a path on disk,
       double check that the name does not contain path traversal attempts
       after basic input validation */
    bool valid_username = false;
    if (validate_username(pUsername) != 0
        || strstr(pUsername, "..") != NULL
        || strstr(pUsername, "/") != NULL
        || strstr(pUsername, ":") != NULL) {
        valid_username = false;
    } else {
        valid_username = true;
    }
#ifdef ENABLE_AUTHHANDLER
    if (valid_username == true) {
        valid_username = mig_validate_username(pUsername);
    }
    if (valid_username == false) {
        WRITELOGMESSAGE(LOG_DEBUG, "valid_username: %d\n",
                valid_username);
        register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                      | MIG_AUTHTYPE_PASSWORD
                      | MIG_INVALID_USERNAME,
                      pUsername, pAddress, NULL);
    }
#endif              /* ENABLE_AUTHHANDLER */
    if (valid_username == false) {
        return PAM_AUTH_ERR;
    }

    /* Check password */

    WRITELOGMESSAGE(LOG_DEBUG, "Checking pw entry for '%s'\n", pUsername);
    struct passwd *pw = getpwnam(pUsername);
    if (pw == NULL) {
        WRITELOGMESSAGE(LOG_INFO, "User not found: %s\n", pUsername);
#ifdef ENABLE_AUTHHANDLER
        register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                      | MIG_AUTHTYPE_PASSWORD
                      | MIG_INVALID_USER,
                      pUsername, pAddress, NULL);
#endif              /* ENABLE_AUTHHANDLER */
        return PAM_AUTH_ERR;
    }
    const char *pPassword;
    retval = pam_get_item(pamh, PAM_AUTHTOK, (const void **)&pPassword);
    if (retval != PAM_SUCCESS) {
        WRITELOGMESSAGE(LOG_INFO, "Failed to get password token\n");
        return retval;
    }
    if (pPassword == NULL) {
        WRITELOGMESSAGE(LOG_DEBUG, "No password, requesting one ...\n");

        struct pam_message msg[1], *pmsg[1];
        struct pam_response *resp;
        pmsg[0] = &msg[0];
        msg[0].msg_style = PAM_PROMPT_ECHO_OFF;
        msg[0].msg = "Password: ";
        resp = NULL;

        retval = converse(pamh, 1, pmsg, &resp);
        if (retval != PAM_SUCCESS) {
            WRITELOGMESSAGE(LOG_ERR, "Failed to converse\n");
            return retval;
        }
        if (resp) {
            if ((flags & PAM_DISALLOW_NULL_AUTHTOK)
                && resp[0].resp == NULL) {
                WRITELOGMESSAGE(LOG_INFO,
                        "Failed with nullauth\n");
                free(resp);
                return PAM_AUTH_ERR;
            }
            WRITELOGMESSAGE(LOG_DEBUG,
                    "Got user password, checking correctness ...\n");
            pPassword = resp[0].resp;
            resp[0].resp = NULL;
        } else {
            WRITELOGMESSAGE(LOG_ERR, "Failed to converse - 2\n");
            return PAM_CONV_ERR;
        }
    }
    const char *pService;
    retval = pam_get_item(pamh, PAM_SERVICE, (const void **)&pService);
    if (retval != PAM_SUCCESS) {
        WRITELOGMESSAGE(LOG_ERR, "Failed to get service name\n");
        return retval;
    }
#ifdef ENABLE_SHARELINK
    /* Optional anonymous share link access:
       - username must have fixed length matching get_sharelink_length()
       - get_sharelink_home()/SHARELINK_SUBDIR/username must exist as a symlink
       - username and password must be identical
     */
    WRITELOGMESSAGE(LOG_DEBUG, "Checking for sharelink: %s\n", pUsername);
    if (strlen(pUsername) == get_sharelink_length()) {
        char share_path[MAX_PATH_LENGTH];
        if (MAX_PATH_LENGTH ==
            snprintf(share_path, MAX_PATH_LENGTH, "%s/%s/%s",
                 get_sharelink_home(), SHARELINK_SUBDIR,
                 pUsername)) {
            WRITELOGMESSAGE(LOG_WARNING,
                    "Path construction failed for: %s/%s/%s\n",
                    get_sharelink_home(), SHARELINK_SUBDIR,
                    pUsername);
            return PAM_AUTH_ERR;
        }
        /* NSS lookup assures sharelink target is valid and inside user home */
        /* Just check simple access here to make sure it is a share link */
        if (access(share_path, R_OK) == 0) {
            WRITELOGMESSAGE(LOG_DEBUG,
                    "Checking sharelink id %s password\n",
                    pUsername);
            if (strcmp(pUsername, pPassword) == 0) {
                WRITELOGMESSAGE(LOG_DEBUG,
                        "Return sharelink success\n");
#ifdef ENABLE_AUTHHANDLER
                register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                              | MIG_SKIP_NOTIFY
                              | MIG_AUTHTYPE_PASSWORD
                              | MIG_AUTHTYPE_ENABLED
                              | MIG_VALID_AUTH,
                              pUsername,
                              pAddress, pPassword);
#endif              /* ENABLE_AUTHHANDLER */
                return PAM_SUCCESS;
            } else {
                WRITELOGMESSAGE(LOG_WARNING,
                        "Username and password mismatch for sharelink: %s\n",
                        pUsername);
#ifdef ENABLE_AUTHHANDLER
                register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                              | MIG_SKIP_NOTIFY
                              | MIG_AUTHTYPE_PASSWORD
                              | MIG_AUTHTYPE_ENABLED
                              | MIG_INVALID_AUTH,
                              pUsername,
                              pAddress, pPassword);
#endif              /* ENABLE_AUTHHANDLER */
                return PAM_AUTH_ERR;
            }
        } else {
            WRITELOGMESSAGE(LOG_DEBUG,
                    "No matching sharelink: %s. Try next auth.\n",
                    share_path);
        }
    } else {
        WRITELOGMESSAGE(LOG_DEBUG,
                "Not a sharelink username: %s. Try next auth.\n",
                pUsername);
    }
#endif              /* ENABLE_SHARELINK */

#ifdef ENABLE_JOBSIDMOUNT
    /* Optional job interactive home access with SID:
       - username must have fixed length matching get_jobsidmount_length()
       - get_jobsidmount_home()/username must exist as a symlink
       - username and password must be identical
     */
    WRITELOGMESSAGE(LOG_DEBUG, "Checking for jobsidmount: %s\n", pUsername);
    if (strlen(pUsername) == get_jobsidmount_length()) {
        char share_path[MAX_PATH_LENGTH];
        if (MAX_PATH_LENGTH ==
            snprintf(share_path, MAX_PATH_LENGTH, "%s/%s",
                 get_jobsidmount_home(), pUsername)) {
            WRITELOGMESSAGE(LOG_WARNING,
                    "Path construction failed for: %s/%s\n",
                    get_jobsidmount_home(), pUsername);
            return PAM_AUTH_ERR;
        }
        /* NSS lookup assures jobsidmount target is valid and inside user home */
        /* Just check simple access here to make sure it is a job session link */
        if (access(share_path, R_OK) == 0) {
#ifdef DISABLE_JOBSIDMOUNT_WITH_PASSWORD
            WRITELOGMESSAGE(LOG_INFO,
                    "Password login not enabled for jobsidmount - use key!\n");
#ifdef ENABLE_AUTHHANDLER
            register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                          | MIG_AUTHTYPE_PASSWORD
                          | MIG_AUTHTYPE_DISABLED,
                          pUsername,
                          pAddress, pPassword);
#endif              /* ENABLE_AUTHHANDLER */
            return PAM_AUTH_ERR;
#endif              /* DISABLE_JOBSIDMOUNT_WITH_PASSWORD */
            WRITELOGMESSAGE(LOG_DEBUG,
                    "Checking jobsidmount %s password\n",
                    pUsername);
            if (strcmp(pUsername, pPassword) == 0) {
                WRITELOGMESSAGE(LOG_DEBUG,
                        "Return jobsidmount success\n");
#ifdef ENABLE_AUTHHANDLER
                register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                              | MIG_SKIP_NOTIFY
                              | MIG_AUTHTYPE_PASSWORD
                              | MIG_AUTHTYPE_ENABLED
                              | MIG_VALID_AUTH,
                              pUsername,
                              pAddress, pPassword);
#endif              /* ENABLE_AUTHHANDLER */
                return PAM_SUCCESS;
            } else {
                WRITELOGMESSAGE(LOG_WARNING,
                        "Username and password mismatch for jobsidmount: %s\n",
                        pUsername);
#ifdef ENABLE_AUTHHANDLER
                register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                              | MIG_SKIP_NOTIFY
                              | MIG_AUTHTYPE_PASSWORD
                              | MIG_AUTHTYPE_ENABLED
                              | MIG_INVALID_AUTH,
                              pUsername,
                              pAddress, pPassword);
#endif              /* ENABLE_AUTHHANDLER */
                return PAM_AUTH_ERR;
            }
        } else {
            WRITELOGMESSAGE(LOG_DEBUG,
                    "No matching jobsidmount: %s. Try next auth.\n",
                    share_path);
        }
    } else {
        WRITELOGMESSAGE(LOG_DEBUG,
                "Not a jobsidmount username: %s. Try next auth.\n",
                pUsername);
    }
#endif              /* ENABLE_JOBSIDMOUNT */

#ifdef ENABLE_JUPYTERSIDMOUNT
    /* Optional jupyter interactive home access with SID:
       - username must have fixed length matching get_jupytersidmount_length()
       - get_jupytersidmount_home()/username must exist as a symlink
       - username and password must be identical
     */
    WRITELOGMESSAGE(LOG_DEBUG, "Checking for jupytersidmount: %s\n",
            pUsername);
    if (strlen(pUsername) == get_jupytersidmount_length()) {
        char share_path[MAX_PATH_LENGTH];
        if (MAX_PATH_LENGTH ==
            snprintf(share_path, MAX_PATH_LENGTH, "%s/%s",
                 get_jupytersidmount_home(), pUsername)) {
            WRITELOGMESSAGE(LOG_WARNING,
                    "Path construction failed for: %s/%s\n",
                    get_jupytersidmount_home(), pUsername);
            return PAM_AUTH_ERR;
        }
        /* NSS lookup assures jupytersidmount target is valid and inside user home */
        /* Just check simple access here to make sure it is a jupyter session link */
        if (access(share_path, R_OK) == 0) {
#ifdef DISABLE_JUPYTERSIDMOUNT_WITH_PASSWORD
            WRITELOGMESSAGE(LOG_INFO,
                "Password login not enabled for jupytersidmount - use key!\n");
#ifdef ENABLE_AUTHHANDLER
            register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                          | MIG_AUTHTYPE_PASSWORD
                          | MIG_AUTHTYPE_DISABLED,
                          pUsername,
                          pAddress, pPassword);
#endif              /* ENABLE_AUTHHANDLER */
            return PAM_AUTH_ERR;
#endif              /* DISABLE_JUPYTERSIDMOUNT_WITH_PASSWORD */
            if (strcmp(pUsername, pPassword) == 0) {
                WRITELOGMESSAGE(LOG_DEBUG,
                        "Return jupytersidmount success\n");
#ifdef ENABLE_AUTHHANDLER
                register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                              | MIG_AUTHTYPE_PASSWORD
                              | MIG_AUTHTYPE_ENABLED
                              | MIG_VALID_AUTH,
                              pUsername,
                              pAddress, pPassword);
#endif              /* ENABLE_AUTHHANDLER */
                return PAM_SUCCESS;
            } else {
                WRITELOGMESSAGE(LOG_WARNING,
                        "Username and password mismatch for jupytersidmount: %s\n",
                        pUsername);
#ifdef ENABLE_AUTHHANDLER
                register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                              | MIG_SKIP_NOTIFY
                              | MIG_AUTHTYPE_PASSWORD
                              | MIG_AUTHTYPE_ENABLED
                              | MIG_INVALID_AUTH,
                              pUsername,
                              pAddress, pPassword);
#endif              /* ENABLE_AUTHHANDLER */
                return PAM_AUTH_ERR;
            }
        } else {
            WRITELOGMESSAGE(LOG_DEBUG,
                    "No matching jupytersidmount: %s. Try next auth.\n",
                    share_path);
        }
    } else {
        WRITELOGMESSAGE(LOG_DEBUG,
                "Not a jupytersidmount username: %s. Try next auth.\n",
                pUsername);
    }
#endif              /* ENABLE_JUPYTERSIDMOUNT */

    WRITELOGMESSAGE(LOG_DEBUG, "Checking for standard user/password: %s\n",
            pUsername);

    /* IMPORTANT: do NOT check password strength for sharelinks/Xsidmount as
       they are NOT guaranteed to follow policy, like character classes
       required.
     */
    /* Assure password follows site policy for length and character classes */
    if (validate_password(pPassword) != 0) {
        WRITELOGMESSAGE(LOG_INFO, "Invalid password from %s\n",
                pUsername);
#ifdef ENABLE_AUTHHANDLER
        register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                      | MIG_AUTHTYPE_PASSWORD
                      | MIG_AUTHTYPE_ENABLED
                      | MIG_INVALID_AUTH,
                      pUsername, pAddress, pPassword);
#endif              /* ENABLE_AUTHHANDLER */
        return PAM_AUTH_ERR;
    }

    char auth_filename[MAX_PATH_LENGTH];
    if (MAX_PATH_LENGTH ==
        snprintf(auth_filename, MAX_PATH_LENGTH, "%s/.%s/%s", pw->pw_dir,
             get_service_dir(pService), PASSWORD_FILENAME)) {
        WRITELOGMESSAGE(LOG_WARNING,
                "Path construction failed for: %s/.%s/%s\n",
                pw->pw_dir, get_service_dir(pService),
                PASSWORD_FILENAME);
        return PAM_AUTH_ERR;
    }

    if (access(auth_filename, F_OK) != 0) {
        WRITELOGMESSAGE(LOG_INFO, "No password file %s found: %s\n",
                auth_filename, strerror(errno));
#ifdef ENABLE_AUTHHANDLER
        register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                      | MIG_AUTHTYPE_PASSWORD
                      | MIG_AUTHTYPE_DISABLED,
                      pUsername, pAddress, pPassword);
#endif              /* ENABLE_AUTHHANDLER */

        return PAM_AUTH_ERR;
    }

    if (access(auth_filename, R_OK) != 0) {
        WRITELOGMESSAGE(LOG_WARNING,
                "Read access to file %s denied: %s\n",
                auth_filename, strerror(errno));
        return PAM_AUTH_ERR;
    }

    struct stat st;
    if (stat(auth_filename, &st) != 0) {
        WRITELOGMESSAGE(LOG_WARNING, "Failed to read file size: %s\n",
                auth_filename);
        return PAM_AUTH_ERR;
    }

    if (st.st_size == 0) {
        WRITELOGMESSAGE(LOG_INFO,
                "Ignoring empty pbkdf digest file: %s\n",
                auth_filename);
        return PAM_AUTH_ERR;
    }

    if (st.st_size > MAX_DIGEST_SIZE) {
        WRITELOGMESSAGE(LOG_WARNING,
                "pbkdf digest file size was %zd but only %d is allowed, filename: %s\n",
                st.st_size, MAX_DIGEST_SIZE, auth_filename);
        return PAM_AUTH_ERR;
    }

    char pbkdf[MAX_DIGEST_SIZE];
    FILE *fd = fopen(auth_filename, "rb");
    if (fd == NULL) {
        WRITELOGMESSAGE(LOG_WARNING,
                "Failed to open file for reading, filename: %s\n",
                auth_filename);
        return PAM_AUTH_ERR;

    }
    if (fread(pbkdf, sizeof(char), st.st_size, fd) != st.st_size) {
        WRITELOGMESSAGE(LOG_WARNING,
                "Failed to read %zd bytes from filename: %s\n",
                st.st_size, auth_filename);
        fclose(fd);
        return PAM_AUTH_ERR;
    }
    fclose(fd);

    //fread does not null terminate the string
    pbkdf[st.st_size] = 0;

    WRITELOGMESSAGE(LOG_DEBUG, "read %s (%zd) from password file", pbkdf,
            strlen(pbkdf));

    if (strstr(pbkdf, "PBKDF2$") != pbkdf) {
        WRITELOGMESSAGE(LOG_WARNING,
                "The pbkdf format was incorrect in file %s\n",
                auth_filename);
        return PAM_AUTH_ERR;
    }

    char *pHashAlg = strchr(pbkdf, '$');
    if (pHashAlg == NULL) {
        WRITELOGMESSAGE(LOG_WARNING,
                "The pbkdf hash algorithm was incorrect in %s\n",
                auth_filename);
        return PAM_AUTH_ERR;
    }

    pHashAlg++;

    char *pItCount = strchr(pHashAlg, '$');
    if (pItCount == NULL) {
        WRITELOGMESSAGE(LOG_WARNING,
                "The pbkdf iteration count was incorrect in %s\n",
                auth_filename);
        return PAM_AUTH_ERR;
    }

    *pItCount = 0;
    pItCount++;

    char *pBase64Salt = strchr(pItCount, '$');
    if (pBase64Salt == NULL) {
        WRITELOGMESSAGE(LOG_WARNING,
                "The pbkdf salt was incorrect in %s\n",
                auth_filename);
        return PAM_AUTH_ERR;
    }

    *pBase64Salt = 0;
    pBase64Salt++;

    char *pBase64Hash = strchr(pBase64Salt, '$');
    if (pBase64Hash == NULL) {
        WRITELOGMESSAGE(LOG_WARNING,
                "The pbkdf salt was incorrect in %s\n",
                auth_filename);
        return PAM_AUTH_ERR;
    }

    *pBase64Hash = 0;
    pBase64Hash++;

    long iteration_count = strtol(pItCount, NULL, 10);
    if (iteration_count <= 0) {
        WRITELOGMESSAGE(LOG_WARNING,
                "The pbkdf iteration count was not a correct integer, file: %s\n",
                auth_filename);
        return PAM_AUTH_ERR;
    }

    if (strcmp(pHashAlg, "sha256") != 0) {
        WRITELOGMESSAGE(LOG_WARNING,
                "The hash algorithm should be sha256, but it was %s\n",
                pHashAlg);
        return PAM_AUTH_ERR;
    }

    char pSaltAndHash[MAX_DIGEST_SIZE];

    size_t salt_size = b64_get_decoded_buffer_size(strlen(pBase64Salt));
    size_t hash_size = b64_get_decoded_buffer_size(strlen(pBase64Hash));

    if (hash_size > (256 / 8)) {
        WRITELOGMESSAGE(LOG_WARNING,
                "The hash was size %zd, but it should be at most %d for SHA256\n",
                hash_size, 256 / 8);
        return PAM_AUTH_ERR;
    }

    if (hash_size < MIN_PBKDF_LENGTH) {
        WRITELOGMESSAGE(LOG_WARNING,
                "The hash was size %zd, but it should be at least %d \n",
                hash_size, MIN_PBKDF_LENGTH);
        return PAM_AUTH_ERR;
    }

    if (salt_size + hash_size > MAX_DIGEST_SIZE) {
        WRITELOGMESSAGE(LOG_WARNING,
                "The expanded salt and hash were too big, reading from file: %s\n",
                auth_filename);
        return PAM_AUTH_ERR;
    }

    if (b64_decode
        ((const uint8_t *)pBase64Salt, strlen(pBase64Salt),
         (uint8_t *) pSaltAndHash) != salt_size) {
        WRITELOGMESSAGE(LOG_WARNING,
                "Failed to base64 decode salt from file: %s\n",
                auth_filename);
        return PAM_AUTH_ERR;
    }
    if (b64_decode
        ((const uint8_t *)pBase64Hash, strlen(pBase64Hash),
         (uint8_t *) pSaltAndHash + salt_size) != hash_size) {
        WRITELOGMESSAGE(LOG_WARNING,
                "Failed to base64 decode hash from file: %s\n",
                auth_filename);
        return PAM_AUTH_ERR;
    }

    WRITELOGMESSAGE(LOG_DEBUG,
            "Checking password with pbkdf value from %s ...\n",
            auth_filename);

    char pResult[MAX_DIGEST_SIZE];

    PKCS5_PBKDF2_HMAC((unsigned char *)pPassword,
              strlen(pPassword),
              (unsigned char *)pBase64Salt,
              strlen(pBase64Salt),
              iteration_count, hash_size, (unsigned char *)pResult);

    size_t expaded_hash_size = b64_get_encoded_buffer_size(hash_size);
    if (expaded_hash_size >= MAX_DIGEST_SIZE) {
        WRITELOGMESSAGE(LOG_WARNING,
                "Failed to base64 encode hash from file: %s\n",
                auth_filename);
        return PAM_AUTH_ERR;
    }

    b64_encode((const uint8_t *)pResult, hash_size, (uint8_t *) & pbkdf);
    //b64 encode does not null terminate the string
    pbkdf[expaded_hash_size] = 0;

    if (strcmp(pBase64Hash, pbkdf) != 0) {
        WRITELOGMESSAGE(LOG_INFO,
                "Supplied password did not match the stored pbkdf digest\n");
        WRITELOGMESSAGE(LOG_DEBUG,
                "Supplied password  \"%s\" did not match the stored pbkdf digest \"%s\"\n",
                pbkdf, pBase64Hash);
#ifdef ENABLE_AUTHHANDLER
        register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                      | MIG_AUTHTYPE_PASSWORD
                      | MIG_AUTHTYPE_ENABLED
                      | MIG_INVALID_AUTH,
                      pUsername, pAddress, pPassword);
#endif              /* ENABLE_AUTHHANDLER */
        return PAM_AUTH_ERR;
    }
#ifdef ENABLE_CHROOT
    retval =
        pam_set_data(pamh, PAM_DATA_NAME, PAM_CHROOT_AUTHENTICATED, NULL);
    if (retval != PAM_SUCCESS) {
        WRITELOGMESSAGE(LOG_WARNING, "Failed to get set chroot hook\n");
        return retval;
    }
#endif              /* ENABLE_CHROOT */

#ifdef ENABLE_AUTHHANDLER
    register_auth_attempt(MIG_SKIP_TWOFA_CHECK
                  | MIG_AUTHTYPE_PASSWORD
                  | MIG_AUTHTYPE_ENABLED
                  | MIG_VALID_AUTH, pUsername, pAddress, pPassword);
#endif              /* ENABLE_AUTHHANDLER */
    WRITELOGMESSAGE(LOG_DEBUG, "Return success\n");
    return PAM_SUCCESS;
}
