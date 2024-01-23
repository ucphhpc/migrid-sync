/*
 * libpam_mig - PAM module for MiG user authentication
 * Copyright (C) 2003-2024  The MiG Project lead by Brian Vinter
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

/* Helper to pretty print bool values */
#ifndef BOOL2STR
#define BOOL2STR(x) x ? "true" : "false"
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

static size_t get_password_min_length()
{
    return get_runtime_var_size_t("PASSWORD_MIN_LENGTH",
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
    /* NOTE: always look up and use these to avoid compile warnings */
    const int pw_min_len = get_password_min_length();
    const int pw_min_cls = get_password_min_classes();
    WRITELOGMESSAGE(LOG_DEBUG, "pw helpers: minlen %d minclass %d\n",
                    pw_min_len, pw_min_cls);

    /* IMPORTANT: do NOT ever log raw password as it makes logs sensitive */
    if (strlen(password) > PASSWORD_MAX_LENGTH) {
        WRITELOGMESSAGE(LOG_INFO,
                        "Invalid password - too long (%zd > %d)\n",
                        strlen(password), PASSWORD_MAX_LENGTH);
        return 2;
    }
    /* IMPORTANT: we rely on checking password policy in python calls wrapping
       args in strings and thus must do very basic input validation to avoid
       quoting interference issues. 
    */
    if (strstr(password, "'") != NULL || strstr(password, "\"") != NULL) {
        WRITELOGMESSAGE(LOG_INFO,
                        "Invalid password - contains quote(s)\n");
        return 3;
    }

    int classes = -1;

#ifdef ENABLE_AUTHHANDLER
    /* NOTE: prefer python assure_password_strength if available */
    bool valid_password = mig_validate_password(password);
    if (valid_password == false) {
        WRITELOGMESSAGE(LOG_INFO, 
                        "password of length %zd failed policy check\n",
                        strlen(password));
        return 1;
    }
#else
    /* NOTE: fall back to static password policy check otherwise */
    if (strlen(password) < pw_min_len) {
        WRITELOGMESSAGE(LOG_INFO,
                        "Invalid password - too short (%zd < %d)\n",
                        strlen(password), pw_min_len);
        return 1;
    }    
    WRITELOGMESSAGE(LOG_DEBUG, "Validated length of password: %zd\n",
                    strlen(password));
    int i;
    /* NOTE: we can safely include a masked password in debug mode */
    char masked[strlen(password)+1];
    for (i = 0; i < strlen(password); i++) {
      masked[i] = '*';
    }
    masked[0] = password[0];
    masked[strlen(password)-1] = password[strlen(password)-1];
    // null terminate the masked string
    masked[strlen(password)] = 0;
    WRITELOGMESSAGE(LOG_DEBUG, "Validate password: %s\n", masked);

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
    if (classes < pw_min_cls) {
        WRITELOGMESSAGE(LOG_INFO,
                        "password has too few character classes (%d < %d)\n",
                        classes, pw_min_cls);
        return 1;
    }
#endif
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

/* this function frees PAM response structures */
static void free_pam_response(struct pam_response *resp, int nargs)
{
    if (resp != NULL) {
        for (int i = 0; i < nargs; i++) {
            if (resp[i].resp != NULL) {
                free(resp[i].resp);
                resp[i].resp = NULL;
            }
        }
        free(resp);
    }
}

/* The do_chroot function invokes chroot to force the user into the home directory */
#ifdef ENABLE_CHROOT
static int do_chroot(pam_handle_t * pamh)
{
    int retval;

    const char *pUsername;
    retval = pam_get_user(pamh, &pUsername, "Username: ");

    if (retval != PAM_SUCCESS) {
        WRITELOGMESSAGE(LOG_WARNING, "PAM could not lookup username ...\n");
        return retval;
    }

    if (pUsername == NULL || strlen(pUsername) == 0) {
        WRITELOGMESSAGE(LOG_INFO, "Did not get a valid username ...\n");
        return PAM_AUTH_ERR;
    }

    /* Since we rely on mapping the username to a path on disk,
       double check that the name does not contain path traversal attempts
       after basic input validation for only safe characters. */
    if (validate_username(pUsername) != 0
        || strstr(pUsername, "..") != NULL
        || strstr(pUsername, "/") != NULL || strstr(pUsername, ":") != NULL) {
        WRITELOGMESSAGE(LOG_INFO,
                        "Username did not pass validation: %s\n", pUsername);
        return PAM_AUTH_ERR;
    }

    struct passwd *pw = getpwnam(pUsername);
    if (pw == NULL) {
        WRITELOGMESSAGE(LOG_INFO, "User not found: %s\n", pUsername);

        return PAM_AUTH_ERR;
    }

    if (chdir(pw->pw_dir) != 0) {
        WRITELOGMESSAGE(LOG_WARNING, "Unable to chdir to %s\n", pw->pw_dir);
        return PAM_AUTH_ERR;
    }

    WRITELOGMESSAGE(LOG_DEBUG, "Activating chroot for '%s': %s\n",
                    pUsername, pw->pw_dir);
    if (chroot(pw->pw_dir) == 0) {
        WRITELOGMESSAGE(LOG_DEBUG, "Chroot activated (%s)!\n", strerror(errno));
        if (chdir("/") != 0) {
            WRITELOGMESSAGE(LOG_WARNING, "Unable to chdir to / after chroot\n");
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
#endif                          /* ENABLE_CHROOT */

PAM_EXTERN int pam_sm_close_session(pam_handle_t * pamh, int flags,
                                    int argc, const char **argv)
{
    WRITELOGMESSAGE(LOG_DEBUG, "pam_sm_close_session: %i, %i\n", flags, argc);
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_open_session(pam_handle_t * pamh, int flags,
                                   int argc, const char **argv)
{
    WRITELOGMESSAGE(LOG_DEBUG, "pam_sm_open_session: %i, %i\n", flags, argc);

#ifdef ENABLE_CHROOT
    int retval;

    // TODO: Check if the user is a mig-mapped user,
    // otherwise, do not chroot it

    const void *val;
    retval = pam_get_data(pamh, PAM_DATA_NAME, &val);
    if (retval == PAM_SUCCESS && val == PAM_CHROOT_AUTHENTICATED) {
        retval = pam_set_data(pamh, PAM_DATA_NAME, PAM_CHROOT_REQUEST, NULL);
        if (retval != PAM_SUCCESS) {
            WRITELOGMESSAGE(LOG_WARNING, "Failed to get set chroot hook\n");
            return retval;
        } else {
            WRITELOGMESSAGE(LOG_DEBUG, "Registered for chroot \n");
        }
    }
#endif                          /* ENABLE_CHROOT */

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
        retval = pam_set_data(pamh, PAM_DATA_NAME, PAM_CHROOT_COMPLETED, NULL);
        if (retval != PAM_SUCCESS) {
            WRITELOGMESSAGE(LOG_WARNING, "Failed to get unset chroot hook\n");
            return retval;
        }
        return do_chroot(pamh);
    }
#endif                          /* ENABLE_CHROOT */

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

int pam_sm_authenticate_init()
{
    /* change euid and egid to MiG user */

    int cur_euid = geteuid();
    int cur_egid = getegid();

    if (cur_egid != MIG_GID && setegid(MIG_GID) != 0) {
        WRITELOGMESSAGE(LOG_ERR, "setegid: %s", strerror(errno));
        return PAM_AUTH_ERR;
    }

    if (cur_euid != MIG_UID && seteuid(MIG_UID) != 0) {
        WRITELOGMESSAGE(LOG_ERR, "seteuid: %s", strerror(errno));
        return PAM_AUTH_ERR;
    }
#ifdef DEBUG
    WRITELOGMESSAGE(LOG_DEBUG, "Changed euid: %d -> %d, egid: %d -> %d\n",
                    cur_euid, geteuid(), cur_egid, getegid());
#endif                          /* DEBUG */
#ifdef ENABLE_AUTHHANDLER
    mig_pyinit();
#endif                          /* ENABLE_AUTHHANDLER */
    return PAM_SUCCESS;
}

int pam_sm_authenticate_exit(int exit_value, struct pam_response *pwresp)
{
    int result = exit_value;
    /* Free password response struct */
    free_pam_response(pwresp, 1);
#ifdef ENABLE_AUTHHANDLER
    if (false == mig_pyexit()) {
        result = PAM_AUTH_ERR;
    }
#endif                          /* ENABLE_AUTHHANDLER */
    /* change euid and egid  back to user root */
    int cur_euid = geteuid();
    int cur_egid = getegid();
    if (cur_egid != 0 && setegid(0) != 0) {
        WRITELOGMESSAGE(LOG_ERR, "setegid: %s", strerror(errno));
        result = PAM_AUTH_ERR;
    }
    if (cur_euid != 0 && seteuid(0) != 0) {
        WRITELOGMESSAGE(LOG_ERR, "seteuid: %s", strerror(errno));
        result = PAM_AUTH_ERR;
    }
#ifdef DEBUG
    WRITELOGMESSAGE(LOG_DEBUG, "Changed euid: %d -> %d, egid: %d -> %d\n",
                    cur_euid, geteuid(), cur_egid, getegid());
#endif                          /* DEBUG */
    return result;
}

/* expected hook, this is where custom stuff happens */
PAM_EXTERN int pam_sm_authenticate(pam_handle_t * pamh, int flags,
                                   int argc, const char **argv)
{
    int retval;
    struct pam_response *pwresp = NULL;

    WRITELOGMESSAGE(LOG_DEBUG,
                    "In pam_sm_authenticate: pamh=%p flags=%x, argc=%d, argv:%p\n",
                    (void *)pamh, flags, argc, (void *)argv);

    retval = pam_sm_authenticate_init();
    if (retval != PAM_SUCCESS) {
        return pam_sm_authenticate_exit(retval, pwresp);
    }
#ifdef ENABLE_AUTHHANDLER

    /* Resolve ip address */

    const char *pHostname;
    const char *pAddress = NULL;
    char address[INET_ADDRSTRLEN];
    struct addrinfo *pAddrinfo;
    struct sockaddr_in *ipv4;

    retval = pam_get_item(pamh, PAM_RHOST, (const void **)&pHostname);
    if (retval != PAM_SUCCESS || pHostname == NULL || strlen(pHostname) == 0) {
        WRITELOGMESSAGE(LOG_ERR, "Unable to resolve remote host ...\n");
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    retval = getaddrinfo(pHostname, NULL, NULL, &pAddrinfo);
    if (retval != 0) {
        WRITELOGMESSAGE(LOG_ERR,
                        "Unable to resolve address from host: %s, err: %s\n",
                        pHostname, strerror(errno));
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    ipv4 = (struct sockaddr_in *)pAddrinfo->ai_addr;
    pAddress = inet_ntop(AF_INET, &(ipv4->sin_addr), address, INET_ADDRSTRLEN);
    freeaddrinfo(pAddrinfo);

    if (NULL == inet_ntop(AF_INET, &(ipv4->sin_addr), address, INET_ADDRSTRLEN)) {
        WRITELOGMESSAGE(LOG_ERR,
                        "Unable to resolve address from host: %s, err: %s\n",
                        pHostname, strerror(errno));
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    WRITELOGMESSAGE(LOG_DEBUG,
                    "Resolved remote address: %s from host: %s\n", pAddress,
                    pHostname);
#endif                          /* ENABLE_AUTHHANDLER */

    /* Check PAM user */

    const char *pUsername;
    /* Build and use a python-safe copy of pUsername to avoid problems */
    char safeUsername[USERNAME_MAX_LENGTH+1] = "";
    retval = pam_get_user(pamh, &pUsername, "Username: ");
    /* IMPORTANT: NEVER use pUsername directly in python calls!
       It may contain all kinds of nasty characters to cause security issues.
    */
    if (retval != PAM_SUCCESS || pUsername == NULL || strlen(pUsername) == 0) {
        WRITELOGMESSAGE(LOG_WARNING, "Did not get a valid username ...\n");
#ifdef ENABLE_AUTHHANDLER
        /* NOTE: We explicitly use (empty) safeUsername to avoid unsafe use */
        mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                              | MIG_AUTHTYPE_PASSWORD
                              | MIG_INVALID_USERNAME,
                              safeUsername, pAddress, NULL);
#endif                          /* ENABLE_AUTHHANDLER */
        if (retval != PAM_SUCCESS) {
            return pam_sm_authenticate_exit(retval, pwresp);
        } else {
            return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
        }
    }

    /* Basic validation of username before use anywhere in paths or python */

    /* Since we rely on mapping the username to a path on disk,
       double check that the name does not contain path traversal attempts
       after basic input validation for only safe characters. */
    bool valid_username = false;
    if (validate_username(pUsername) != 0
        || strstr(pUsername, "..") != NULL
        || strstr(pUsername, "/") != NULL || strstr(pUsername, ":") != NULL) {
        valid_username = false;
        /* pUsername may be dangerous here - use a static marker instead */
        snprintf(safeUsername, USERNAME_MAX_LENGTH, "%s", "_UNSAFE_");
    } else {
        valid_username = true;
        /* pUsername is validated enough to be safely used in python calls */
        if (USERNAME_MAX_LENGTH ==
            snprintf(safeUsername, USERNAME_MAX_LENGTH, "%s", pUsername)) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "Safe username construction failed for: %s\n",
                            pUsername);
            return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
        }

    }

#ifdef ENABLE_AUTHHANDLER

    /* Check MiG ratelimit */

    int rate_limit_expired = mig_expire_rate_limit();
    WRITELOGMESSAGE(LOG_DEBUG, "rate_limit_expired: %d\n", rate_limit_expired);
    bool exceeded_rate_limit = mig_hit_rate_limit(safeUsername, pAddress);
    WRITELOGMESSAGE(LOG_DEBUG, "exceeded_rate_limit: %s\n",
                    BOOL2STR(exceeded_rate_limit));
    if (exceeded_rate_limit == true) {
        if (true == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                          | MIG_AUTHTYPE_PASSWORD
                                          | MIG_EXCEEDED_RATE_LIMIT,
                                          safeUsername, pAddress, NULL)) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "MiG registered successful auth despite NOT PAM_SUCCESS");
        }
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    /* check MiG max sftp sessions */

    /*** 
     * NOTE: Disabled for now, 
     * this requires session open/close tracking in sftp_subsys.py 
     
    bool exceeded_max_sessions = mig_exceeded_max_sessions(safeUsername,
                                                           pAddress);
    WRITELOGMESSAGE(LOG_DEBUG, "exceeded_max_sessions: %s\n",
                    BOOL2STR(exceeded_max_sessions));
    if (exceeded_max_sessions == true) {
        if (true == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                          | MIG_AUTHTYPE_PASSWORD
                                          | MIG_EXCEEDED_MAX_SESSIONS,
                                          safeUsername, pAddress, NULL)) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "MiG registered successful auth despite NOT PAM_SUCCESS");
        }
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }
    ***/
#endif                          /* ENABLE_AUTHHANDLER */

#ifdef ENABLE_AUTHHANDLER
    if (valid_username == true) {
        valid_username = mig_validate_username(safeUsername);
    }
    if (valid_username == false) {
        WRITELOGMESSAGE(LOG_DEBUG, "valid_username: %s\n",
                        BOOL2STR(valid_username));
        if (true == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                          | MIG_AUTHTYPE_PASSWORD
                                          | MIG_INVALID_USERNAME,
                                          safeUsername, pAddress, NULL)) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "MiG registered successful auth despite NOT PAM_SUCCESS");
        }
    } else {
        /* Check account active and not expired */
        valid_username = mig_check_account_accessible(safeUsername);
        if (valid_username == false) {
            WRITELOGMESSAGE(LOG_DEBUG, "account_accessible: %s\n",
                            BOOL2STR(valid_username));
            if (true == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                              | MIG_AUTHTYPE_PASSWORD
                                              | MIG_ACCOUNT_INACCESSIBLE,
                                              safeUsername, pAddress, NULL)) {
                WRITELOGMESSAGE(LOG_WARNING,
                                "MiG registered successful auth despite NOT PAM_SUCCESS");
            }
        }
    }
#endif                          /* ENABLE_AUTHHANDLER */
    if (valid_username == false) {
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    /* Check password */

    WRITELOGMESSAGE(LOG_DEBUG, "Checking pw entry for '%s'\n", pUsername);
    struct passwd *pw = getpwnam(pUsername);
    if (pw == NULL) {
        WRITELOGMESSAGE(LOG_INFO, "User not found: %s\n", pUsername);
#ifdef ENABLE_AUTHHANDLER
        if (true == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                          | MIG_AUTHTYPE_PASSWORD
                                          | MIG_INVALID_USER, safeUsername,
                                          pAddress, NULL)) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "MiG registered successful auth despite NOT PAM_SUCCESS");
        }
#endif                          /* ENABLE_AUTHHANDLER */
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }
    const char *pPassword;
    retval = pam_get_item(pamh, PAM_AUTHTOK, (const void **)&pPassword);
    if (retval != PAM_SUCCESS) {
        WRITELOGMESSAGE(LOG_INFO, "Failed to get password token\n");
        return pam_sm_authenticate_exit(retval, pwresp);
    }
    if (pPassword == NULL) {
        WRITELOGMESSAGE(LOG_DEBUG, "No password, requesting one ...\n");

        struct pam_message msg[1], *pmsg[1];
        pmsg[0] = &msg[0];
        msg[0].msg_style = PAM_PROMPT_ECHO_OFF;
        msg[0].msg = "Password: ";

        retval = converse(pamh, 1, pmsg, &pwresp);
        if (retval != PAM_SUCCESS) {
            WRITELOGMESSAGE(LOG_ERR, "Failed to converse\n");
            return pam_sm_authenticate_exit(retval, pwresp);
        }
        if (pwresp) {
            if ((flags & PAM_DISALLOW_NULL_AUTHTOK)
                && pwresp[0].resp == NULL) {
                WRITELOGMESSAGE(LOG_INFO, "Failed with nullauth\n");
                return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
            }
            WRITELOGMESSAGE(LOG_DEBUG,
                            "Got user password, checking correctness ...\n");
            pPassword = pwresp[0].resp;
        } else {
            WRITELOGMESSAGE(LOG_ERR, "Failed to converse - 2\n");
            return pam_sm_authenticate_exit(PAM_CONV_ERR, pwresp);
        }
    }
    const char *pService;
    retval = pam_get_item(pamh, PAM_SERVICE, (const void **)&pService);
    if (retval != PAM_SUCCESS) {
        WRITELOGMESSAGE(LOG_ERR, "Failed to get service name\n");
        return pam_sm_authenticate_exit(retval, pwresp);
    }
#ifdef ENABLE_AUTHHANDLER
    /* IMPORTANT: pass a hashed version of the base64 encoded password to
       mig_reg_auth_attempt, since we NEVER want raw passwords on disk.
       The base64 encoding is applied to make sure we have a quoting-safe 
       version to string-expand in the python function call. Otherwise we
       might hit quoting issues for raw passwords containing single or double
       quotes, because we only check valid chars later.
    */
    char encpw[MAX_DIGEST_SIZE];
    size_t encpw_size = b64_get_encoded_buffer_size(strlen(pPassword));
    if (encpw_size >= MAX_DIGEST_SIZE) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "Cannot build hash from password of extreme length: %d\n",
                        (uint)strlen(pPassword));
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }
    b64_encode((const uint8_t *)pPassword, encpw_size, (uint8_t *) & encpw);
    //b64 encode does not null terminate the string
    encpw[encpw_size] = 0;

    char *pHash = mig_make_simple_hash(encpw);
    WRITELOGMESSAGE(LOG_DEBUG, "pHash: %s\n", pHash);
#endif
#ifdef ENABLE_SHARELINK
    /* Optional anonymous share link access:
       - username must have fixed length matching get_sharelink_length()
       - get_sharelink_home()/SHARELINK_SUBDIR/username must exist as a symlink
       - username and password must be identical if we get here (key skips PAM)
     */
    WRITELOGMESSAGE(LOG_DEBUG, "Checking for sharelink: %s\n", pUsername);
    if (strlen(pUsername) == get_sharelink_length()) {
        char share_path[MAX_PATH_LENGTH];
        if (MAX_PATH_LENGTH ==
            snprintf(share_path, MAX_PATH_LENGTH, "%s/%s/%s",
                     get_sharelink_home(), SHARELINK_SUBDIR, pUsername)) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "Path construction failed for: %s/%s/%s\n",
                            get_sharelink_home(), SHARELINK_SUBDIR, pUsername);
            return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
        }
        /* NSS lookup assures sharelink target is valid and inside user home */
        /* Just check simple access here to make sure it is a share link */
        if (access(share_path, R_OK) == 0) {
            WRITELOGMESSAGE(LOG_DEBUG,
                            "Checking sharelink id %s password\n", pUsername);
            if (strcmp(pUsername, pPassword) == 0) {
                WRITELOGMESSAGE(LOG_DEBUG, "Return sharelink success\n");
#ifdef ENABLE_AUTHHANDLER
                if (false == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                                   | MIG_SKIP_NOTIFY
                                                   | MIG_AUTHTYPE_PASSWORD
                                                   | MIG_AUTHTYPE_ENABLED
                                                   | MIG_VALID_AUTH,
                                                   safeUsername, pAddress,
                                                   pHash)) {
                    return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
                }
#endif                          /* ENABLE_AUTHHANDLER */
                return pam_sm_authenticate_exit(PAM_SUCCESS, pwresp);
            } else {
                WRITELOGMESSAGE(LOG_WARNING,
                                "Username and password mismatch for sharelink: %s\n",
                                pUsername);
#ifdef ENABLE_AUTHHANDLER
                if (true == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                                  | MIG_SKIP_NOTIFY
                                                  | MIG_AUTHTYPE_PASSWORD
                                                  | MIG_AUTHTYPE_ENABLED
                                                  | MIG_INVALID_AUTH,
                                                  safeUsername, pAddress,
                                                  pHash)) {
                    WRITELOGMESSAGE(LOG_WARNING,
                                    "MiG registered successful auth despite NOT PAM_SUCCESS");
                }
#endif                          /* ENABLE_AUTHHANDLER */
                return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
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
#endif                          /* ENABLE_SHARELINK */

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
            return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
        }
        /* NSS lookup assures jobsidmount target is valid and inside user home */
        /* Just check simple access here to make sure it is a job session link */
        if (access(share_path, R_OK) == 0) {
#ifdef DISABLE_JOBSIDMOUNT_WITH_PASSWORD
            WRITELOGMESSAGE(LOG_INFO,
                            "Password login not enabled for jobsidmount - use key!\n");
#ifdef ENABLE_AUTHHANDLER
            if (true == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                              | MIG_AUTHTYPE_PASSWORD
                                              | MIG_AUTHTYPE_DISABLED,
                                              safeUsername, pAddress, pHash)) {
                WRITELOGMESSAGE(LOG_WARNING,
                                "MiG registered successful auth despite NOT PAM_SUCCESS");
            }
#endif                          /* ENABLE_AUTHHANDLER */
            return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
#endif                          /* DISABLE_JOBSIDMOUNT_WITH_PASSWORD */
            WRITELOGMESSAGE(LOG_DEBUG,
                            "Checking jobsidmount %s password\n", pUsername);
            if (strcmp(pUsername, pPassword) == 0) {
                WRITELOGMESSAGE(LOG_DEBUG, "Return jobsidmount success\n");
#ifdef ENABLE_AUTHHANDLER
                if (false == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                                   | MIG_SKIP_NOTIFY
                                                   | MIG_AUTHTYPE_PASSWORD
                                                   | MIG_AUTHTYPE_ENABLED
                                                   | MIG_VALID_AUTH,
                                                   safeUsername, pAddress,
                                                   pHash)) {
                    return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
                }
#endif                          /* ENABLE_AUTHHANDLER */
                return pam_sm_authenticate_exit(PAM_SUCCESS, pwresp);
            } else {
                WRITELOGMESSAGE(LOG_WARNING,
                                "Username and password mismatch for jobsidmount: %s\n",
                                pUsername);
#ifdef ENABLE_AUTHHANDLER
                if (true == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                                  | MIG_SKIP_NOTIFY
                                                  | MIG_AUTHTYPE_PASSWORD
                                                  | MIG_AUTHTYPE_ENABLED
                                                  | MIG_INVALID_AUTH,
                                                  safeUsername, pAddress,
                                                  pHash)) {
                    WRITELOGMESSAGE(LOG_WARNING,
                                    "MiG registered successful auth despite NOT PAM_SUCCESS");
                }
#endif                          /* ENABLE_AUTHHANDLER */
                return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
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
#endif                          /* ENABLE_JOBSIDMOUNT */

#ifdef ENABLE_JUPYTERSIDMOUNT
    /* Optional jupyter interactive home access with SID:
       - username must have fixed length matching get_jupytersidmount_length()
       - get_jupytersidmount_home()/username must exist as a symlink
       - username and password must be identical
     */
    WRITELOGMESSAGE(LOG_DEBUG, "Checking for jupytersidmount: %s\n", pUsername);
    if (strlen(pUsername) == get_jupytersidmount_length()) {
        char share_path[MAX_PATH_LENGTH];
        if (MAX_PATH_LENGTH ==
            snprintf(share_path, MAX_PATH_LENGTH, "%s/%s",
                     get_jupytersidmount_home(), pUsername)) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "Path construction failed for: %s/%s\n",
                            get_jupytersidmount_home(), pUsername);
            return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
        }
        /* NSS lookup assures jupytersidmount target is valid and inside user home */
        /* Just check simple access here to make sure it is a jupyter session link */
        if (access(share_path, R_OK) == 0) {
#ifdef DISABLE_JUPYTERSIDMOUNT_WITH_PASSWORD
            WRITELOGMESSAGE(LOG_INFO,
                            "Password login not enabled for jupytersidmount - use key!\n");
#ifdef ENABLE_AUTHHANDLER
            if (true == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                              | MIG_AUTHTYPE_PASSWORD
                                              | MIG_AUTHTYPE_DISABLED,
                                              safeUsername, pAddress, pHash)) {
                WRITELOGMESSAGE(LOG_WARNING,
                                "MiG registered successful auth despite NOT PAM_SUCCESS");
            }
#endif                          /* ENABLE_AUTHHANDLER */
            return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
#endif                          /* DISABLE_JUPYTERSIDMOUNT_WITH_PASSWORD */
            if (strcmp(pUsername, pPassword) == 0) {
                WRITELOGMESSAGE(LOG_DEBUG, "Return jupytersidmount success\n");
#ifdef ENABLE_AUTHHANDLER
                if (false == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                                   | MIG_AUTHTYPE_PASSWORD
                                                   | MIG_AUTHTYPE_ENABLED
                                                   | MIG_VALID_AUTH,
                                                   safeUsername, pAddress,
                                                   pHash)) {
                    return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
                }
#endif                          /* ENABLE_AUTHHANDLER */
                return pam_sm_authenticate_exit(PAM_SUCCESS, pwresp);
            } else {
                WRITELOGMESSAGE(LOG_WARNING,
                                "Username and password mismatch for jupytersidmount: %s\n",
                                pUsername);
#ifdef ENABLE_AUTHHANDLER
                if (true == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                                  | MIG_SKIP_NOTIFY
                                                  | MIG_AUTHTYPE_PASSWORD
                                                  | MIG_AUTHTYPE_ENABLED
                                                  | MIG_INVALID_AUTH,
                                                  safeUsername, pAddress,
                                                  pHash)) {
                    WRITELOGMESSAGE(LOG_WARNING,
                                    "MiG registered successful auth despite NOT PAM_SUCCESS");
                }
#endif                          /* ENABLE_AUTHHANDLER */
                return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
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
#endif                          /* ENABLE_JUPYTERSIDMOUNT */

    WRITELOGMESSAGE(LOG_DEBUG, "Checking for standard user/password: %s\n",
                    pUsername);

    /* IMPORTANT: do NOT check password strength for sharelinks/Xsidmount as
       they are NOT guaranteed to follow policy, like character classes
       required.
     */
    /* Assure password follows site policy for length and character classes */
    if (validate_password(pPassword) != 0) {
        WRITELOGMESSAGE(LOG_INFO, "Invalid password from %s\n", pUsername);
#ifdef ENABLE_AUTHHANDLER
        if (true == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                          | MIG_AUTHTYPE_PASSWORD
                                          | MIG_AUTHTYPE_ENABLED
                                          | MIG_INVALID_AUTH, safeUsername,
                                          pAddress, pHash)) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "MiG registered successful auth despite NOT PAM_SUCCESS");
        }
#endif                          /* ENABLE_AUTHHANDLER */
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    char auth_filename[MAX_PATH_LENGTH];
    if (MAX_PATH_LENGTH ==
        snprintf(auth_filename, MAX_PATH_LENGTH, "%s/.%s/%s", pw->pw_dir,
                 get_service_dir(pService), PASSWORD_FILENAME)) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "Path construction failed for: %s/.%s/%s\n",
                        pw->pw_dir, get_service_dir(pService),
                        PASSWORD_FILENAME);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    if (access(auth_filename, F_OK) != 0) {
        WRITELOGMESSAGE(LOG_INFO, "No password file %s found: %s\n",
                        auth_filename, strerror(errno));
#ifdef ENABLE_AUTHHANDLER
        if (true == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                          | MIG_AUTHTYPE_PASSWORD
                                          | MIG_AUTHTYPE_DISABLED,
                                          safeUsername, pAddress, pHash)) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "MiG registered successful auth despite NOT PAM_SUCCESS");
        }
#endif                          /* ENABLE_AUTHHANDLER */

        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    if (access(auth_filename, R_OK) != 0) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "Read access to file %s denied: %s\n",
                        auth_filename, strerror(errno));
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    struct stat st;
    if (stat(auth_filename, &st) != 0) {
        WRITELOGMESSAGE(LOG_WARNING, "Failed to read file size: %s\n",
                        auth_filename);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    if (st.st_size == 0) {
        WRITELOGMESSAGE(LOG_INFO,
                        "Ignoring empty pbkdf digest file: %s\n",
                        auth_filename);
#ifdef ENABLE_AUTHHANDLER
        if (true == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                          | MIG_AUTHTYPE_PASSWORD
                                          | MIG_AUTHTYPE_DISABLED,
                                          safeUsername, pAddress, pHash)) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "MiG registered successful auth despite NOT PAM_SUCCESS");
        }
#endif                          /* ENABLE_AUTHHANDLER */
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    if (st.st_size > MAX_DIGEST_SIZE) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "pbkdf digest file size was %zd but only %d is allowed, filename: %s\n",
                        st.st_size, MAX_DIGEST_SIZE, auth_filename);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    char pbkdf[MAX_DIGEST_SIZE];
    FILE *fd = fopen(auth_filename, "rb");
    if (fd == NULL) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "Failed to open file for reading, filename: %s\n",
                        auth_filename);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);

    }
    if (fread(pbkdf, sizeof(char), (size_t)st.st_size, fd) != (size_t)st.st_size) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "Failed to read %zd bytes from filename: %s\n",
                        st.st_size, auth_filename);
        fclose(fd);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
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
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    char *pHashAlg = strchr(pbkdf, '$');
    if (pHashAlg == NULL) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "The pbkdf hash algorithm was incorrect in %s\n",
                        auth_filename);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    pHashAlg++;

    char *pItCount = strchr(pHashAlg, '$');
    if (pItCount == NULL) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "The pbkdf iteration count was incorrect in %s\n",
                        auth_filename);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    *pItCount = 0;
    pItCount++;

    char *pBase64Salt = strchr(pItCount, '$');
    if (pBase64Salt == NULL) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "The pbkdf salt was incorrect in %s\n", auth_filename);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    *pBase64Salt = 0;
    pBase64Salt++;

    char *pBase64Hash = strchr(pBase64Salt, '$');
    if (pBase64Hash == NULL) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "The pbkdf salt was incorrect in %s\n", auth_filename);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    *pBase64Hash = 0;
    pBase64Hash++;

    long iteration_count = strtol(pItCount, NULL, 10);
    if (iteration_count <= 0) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "The pbkdf iteration count was not a correct integer, file: %s\n",
                        auth_filename);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    if (strcmp(pHashAlg, "sha256") != 0) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "The hash algorithm should be sha256, but it was %s\n",
                        pHashAlg);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    char pSaltAndHash[MAX_DIGEST_SIZE];

    size_t salt_size = b64_get_decoded_buffer_size(strlen(pBase64Salt));
    size_t hash_size = b64_get_decoded_buffer_size(strlen(pBase64Hash));

    if (hash_size > (256 / 8)) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "The hash was size %zd, but it should be at most %d for SHA256\n",
                        hash_size, 256 / 8);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    if (hash_size < MIN_PBKDF_LENGTH) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "The hash was size %zd, but it should be at least %d \n",
                        hash_size, MIN_PBKDF_LENGTH);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    if (salt_size + hash_size > MAX_DIGEST_SIZE) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "The expanded salt and hash were too big, reading from file: %s\n",
                        auth_filename);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    if (b64_decode
        ((const uint8_t *)pBase64Salt, strlen(pBase64Salt),
         (uint8_t *) pSaltAndHash) != salt_size) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "Failed to base64 decode salt from file: %s\n",
                        auth_filename);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }
    if (b64_decode
        ((const uint8_t *)pBase64Hash, strlen(pBase64Hash),
         (uint8_t *) pSaltAndHash + salt_size) != hash_size) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "Failed to base64 decode hash from file: %s\n",
                        auth_filename);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
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

    size_t expanded_hash_size = b64_get_encoded_buffer_size(hash_size);
    if (expanded_hash_size >= MAX_DIGEST_SIZE) {
        WRITELOGMESSAGE(LOG_WARNING,
                        "Failed to base64 encode hash from file: %s\n",
                        auth_filename);
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }

    b64_encode((const uint8_t *)pResult, hash_size, (uint8_t *) & pbkdf);
    //b64 encode does not null terminate the string
    pbkdf[expanded_hash_size] = 0;

    if (strcmp(pBase64Hash, pbkdf) != 0) {
        WRITELOGMESSAGE(LOG_INFO,
                        "Supplied password did not match the stored pbkdf digest\n");
        WRITELOGMESSAGE(LOG_DEBUG,
                        "Supplied password  \"%s\" did not match the stored pbkdf digest \"%s\"\n",
                        pbkdf, pBase64Hash);
#ifdef ENABLE_AUTHHANDLER
        if (true == mig_reg_auth_attempt(MIG_SKIP_TWOFA_CHECK
                                          | MIG_AUTHTYPE_PASSWORD
                                          | MIG_AUTHTYPE_ENABLED
                                          | MIG_INVALID_AUTH, safeUsername,
                                          pAddress, pHash)) {
            WRITELOGMESSAGE(LOG_WARNING,
                            "MiG registered successful auth despite NOT PAM_SUCCESS");
        }
#endif                          /* ENABLE_AUTHHANDLER */
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }
#ifdef ENABLE_CHROOT
    retval = pam_set_data(pamh, PAM_DATA_NAME, PAM_CHROOT_AUTHENTICATED, NULL);
    if (retval != PAM_SUCCESS) {
        WRITELOGMESSAGE(LOG_WARNING, "Failed to get set chroot hook\n");
        return pam_sm_authenticate_exit(retval, pwresp);
    }
#endif                          /* ENABLE_CHROOT */

#ifdef ENABLE_AUTHHANDLER
    unsigned int mode = MIG_AUTHTYPE_PASSWORD
        | MIG_AUTHTYPE_ENABLED | MIG_VALID_AUTH;
    if (true == mig_check_twofactor_session(safeUsername, pAddress)) {
        mode |= MIG_VALID_TWOFA;
    }
    if (false == mig_reg_auth_attempt(mode, safeUsername, pAddress, pHash)) {
        return pam_sm_authenticate_exit(PAM_AUTH_ERR, pwresp);
    }
#endif                          /* ENABLE_AUTHHANDLER */
    WRITELOGMESSAGE(LOG_DEBUG, "Return success\n");
    return pam_sm_authenticate_exit(PAM_SUCCESS, pwresp);
}
