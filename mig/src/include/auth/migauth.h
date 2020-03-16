/*
 * migauth.h - PAM and NSS helpers for MiG user authentication
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
 * Helpers for supporting native login of MiG virtual users. This module
 * contains various helpers to check if a user exists in the MiG system, and
 * map such users to the mig-user UID and GID, but with a custom home folder.
 *
 * Written by Kenneth Skovhede <skovhede@nbi.ku.dk>
 * Extended for sharelinks by Jonas Bardino <bardino@nb.ku.dk>
 * Extended for GDB debugging by Martin Rehr <rehr@nbi.ku.dk>
 *
 */

#ifndef _MIGAUTH_H_
#define _MIGAUTH_H_

#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <ctype.h>
#include <regex.h>
#include <stdarg.h>
#include <syslog.h>
#include <signal.h>
/* TODO: enable conf parsing with this:
#include <ini_config.h>
*/

#ifndef MIG_UID
#define MIG_UID 501
#endif

#ifndef MIG_GID
#define MIG_GID 501
#endif

#define PASSWORD_FILENAME "authorized_passwords"

/* Various settings used for username input validation */
/* Something similar to most UN*X account name restrictions */
#ifndef USERNAME_REGEX
/* Default fall-back value used unless given */
/* NOTE: line anchors are mandatory to avoid false hits */
#define USERNAME_REGEX "^[a-z0-9][a-z0-9_-]{1,127}$"
#endif
#ifndef USERNAME_MIN_LENGTH
/* Default fall-back value used unless given */
#define USERNAME_MIN_LENGTH 2
#endif
#ifndef USERNAME_MAX_LENGTH
/* Default fall-back value used unless given */
#define USERNAME_MAX_LENGTH 128
#endif

/* Various settings used by ordinary user access */
#ifndef USER_HOME
#define USER_HOME "/home"
#endif

/* Various settings used by optional auth handler access */
/* Enable auth handler unless explicitly disabled during compilation */
#ifndef DISABLE_AUTHHANDLER
#define ENABLE_AUTHHANDLER 1
#endif                          /* !DISABLE_AUTHHANDLER */

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
#endif                          /* !DISABLE_SHARELINK */

/* Various settings used by optional job session mount access */
/* Enable job session mount unless explicitly disabled during compilation */
#ifndef DISABLE_JOBSIDMOUNT
#define ENABLE_JOBSIDMOUNT 1
/* Disable job session mount with same password as username unless explicitly
   enabled during compilation */
#ifndef ENABLE_JOBSIDMOUNT_WITH_PASSWORD
#define DISABLE_JOBSIDMOUNT_WITH_PASSWORD
#endif
/* Default fall-back values used unless given */
#ifndef JOBSIDMOUNT_HOME
#define JOBSIDMOUNT_HOME "/tmp"
#endif
#ifndef JOBSIDMOUNT_LENGTH
#define JOBSIDMOUNT_LENGTH 42
#endif
#endif                          /* !DISABLE_JOBSIDMOUNT */

/* Various settings used by optional jupyter session mount access */
/* Enable jupyter session mount unless explicitly disabled during compilation */
#ifndef DISABLE_JUPYTERSIDMOUNT
#define ENABLE_JUPYTERSIDMOUNT 1
/* Disable jupyter session mount with same password as username unless
   explicitly enabled during compilation */
#ifndef ENABLE_JUPYTERSIDMOUNT_WITH_PASSWORD
#define DISABLE_JUPYTERSIDMOUNT_WITH_PASSWORD
#endif
/* Default fall-back values used unless given */
#ifndef JUPYTERSIDMOUNT_HOME
#define JUPYTERSIDMOUNT_HOME "/tmp"
#endif
#ifndef JUPYTERSIDMOUNT_LENGTH
#define JUPYTERSIDMOUNT_LENGTH 42
#endif
#endif                          /* !DISABLE_JUPYTERSIDMOUNT */

/* Helper macros that writes messages to syslog  */

/* For testing, log to stderr can be used instead of syslog,
   but should never be enabled in non-debug mode */
//#define DEBUG_LOG_STDERR 1
/* Uncomment to enable debug messages as well */
//#define DEBUG 1

#if defined(DEBUG) || defined(DEBUG_LOG_STDERR)
#define STRINGIFY(x) #x
#define TOSTRING(x) STRINGIFY(x)
#ifdef DEBUG_LOG_STDERR
#define WRITELOGMESSAGE(priority, format, ...) \
    fprintf(stderr, #priority ": " __FILE__"("TOSTRING(__LINE__)"): " format, ##__VA_ARGS__)
#else                           /* DEBUG_LOG_STDERR */
#define WRITELOGMESSAGE(priority, format, ...) \
    openlog("pam_mig", LOG_PID, LOG_AUTHPRIV); \
    syslog(priority, #priority ": " __FILE__"("TOSTRING(__LINE__)"): " format, ##__VA_ARGS__);
#endif                          /* DEBUG_LOG_STDERR */
#else                           /* DEBUG || DEBUG_LOG_STDERR */
#define WRITELOGMESSAGE(priority, format, ...) \
    if (priority != LOG_DEBUG) { \
        openlog("pam_mig", LOG_PID, LOG_AUTHPRIV); \
        syslog(priority, format, ##__VA_ARGS__); \
    }
#endif                          /* DEBUG || DEBUG_LOG_STDERR */

/* Helper functions/macros for GDB debugging */

#ifdef GDB_BREAKPOINT_ENABLED
unsigned int _gdb_console_connected = 0;
void _gdb_handle_sigcont(int signal)
{
    /* NOTE: We do not forward SIGCONT because: 
       You can set a handler, but SIGCONT always makes the process continue regardless:
       https://www.gnu.org/software/libc/manual/html_node/Job-Control-Signals.html 
     */

    if (!_gdb_console_connected) {
        WRITELOGMESSAGE(LOG_DEBUG, "GDB console attached to: %d\n", getpid());
        _gdb_console_connected = 1;
    }
}

/* NOTE: 
First GDB_BREAKPOINT: Register signal handler and wait for GDB console 'signal SIGCONT'
Rest: http://lackingrhoticity.blogspot.com/2010/05/breakpoints-in-gdb-using-int3.htmlint3
*/
#define GDB_BREAKPOINT \
    WRITELOGMESSAGE(LOG_DEBUG, "_GDB_BREAKPOINT: %s(%d)", __FILE__, __LINE__); \
    if (!_gdb_console_connected) { \
        WRITELOGMESSAGE(LOG_DEBUG, "Waiting for GDB console: gdb attach %d\n", getpid()); \
        WRITELOGMESSAGE(LOG_DEBUG, "To continue from GDB console: signal SIGCONT\n"); \
        signal(SIGCONT, _gdb_handle_sigcont); \
        pause(); \
    } else { \
        asm volatile ("int3;"); \
    }
#else                           /* GDB_BREAKPOINT_ENABLED */
#define GDB_BREAKPOINT asm ("nop");
#endif                          /* GDB_BREAKPOINT_ENABLED */

/* General helper to extract variable value. Tries the environment, conf, 
   compile-time definition and default definition in that order until one
   is found */
static const char *get_runtime_var(const char *env_name,
                                   const char *conf_name,
                                   const char *define_val)
{
#ifdef _GNU_SOURCE
    const char *var_val = secure_getenv(env_name);
#else
    const char *var_val = getenv(env_name);
#endif
    /* TODO: actually implement option (2):
       if (var_val == NULL) {
       #ifdef _GNU_SOURCE
       char *conf_path = secure_getenv("MIG_CONF");
       #else
       char *conf_path = getenv("MIG_CONF");
       #endif

       var_val = conf->conf_name;
       }
     */
    /* Fall back to defined value */
    if (var_val == NULL) {
        var_val = define_val;
    }
    WRITELOGMESSAGE(LOG_DEBUG, "Found runtime var value %s\n", var_val);
    return var_val;
}

/* Similar to get_runtime_var but handling integer values */
static const int get_runtime_var_int(const char *env_name,
                                     const char *conf_name,
                                     const int define_val)
{
    /* NOTE: tedious but required juggling between string and integer */
    char val_str[4];
    /* Convert define_val int to '\0'-terminated string */
    snprintf(val_str, 3, "%d", define_val);
    val_str[3] = 0;
    /* Convert lookup back to int */
    return atoi(get_runtime_var(env_name, conf_name, val_str));

}

/* We take first occurence of USERNAME_REGEX from
 * 1. USERNAME_REGEX environment
 * 2. SITE->username_regex (.ini) configuration file
 * 3. USERNAME_REGEX compile time values
 * 4. hard-coded defaults here
 */
static const char *get_username_regex()
{
    return get_runtime_var("USERNAME_REGEX", "username_regex", USERNAME_REGEX);
}

/* We take first occurence of USER_HOME from
 * 1. USER_HOME environment
 * 2. user_home in (.ini) configuration file
 * 3. USER_HOME compile time values
 * 4. hard-coded defaults here
 */
/* TODO: add support for using AUTO for home in nssswitch.conf
static const char *get_user_home()
{
    return get_runtime_var("USER_HOME", "user_home", USER_HOME);
}
*/

#ifndef DISABLE_SHARELINK
/* We take first occurence of SHARELINK_HOME and SHARELINK_LENGTH from
 * 1. SHARELINK_HOME and SHARELINK_LENGTH environment
 * 2. sharelink_home and SITE->sharelink_length in (.ini) configuration file
 * 3. SHARELINK_HOME and SHARELINK_LENGTH compile time values
 * 4. hard-coded defaults here
 */
static const char *get_sharelink_home()
{
    return get_runtime_var("SHARELINK_HOME", "sharelink_home", SHARELINK_HOME);
}

static int get_sharelink_length()
{
    return get_runtime_var_int("SHARELINK_LENGTH",
                               "site->sharelink_length", SHARELINK_LENGTH);
}
#endif

#ifndef DISABLE_JOBSIDMOUNT
/* We take first occurence of JOBSIDMOUNT_HOME and JOBSIDMOUNT_LENGTH from
 * 1. JOBSIDMOUNT_HOME and JOBSIDMOUNT_LENGTH environment
 * 2. jobsidmount_home and SITE->jobsidmount_length in (.ini) configuration file
 * 3. JOBSIDMOUNT_HOME and JOBSIDMOUNT_LENGTH compile time values
 * 4. hard-coded defaults here
 */
static const char *get_jobsidmount_home()
{
    return get_runtime_var("JOBSIDMOUNT_HOME", "jobsidmount_home",
                           JOBSIDMOUNT_HOME);
}

static int get_jobsidmount_length()
{
    return get_runtime_var_int("JOBSIDMOUNT_LENGTH",
                               "site->jobsidmount_length", JOBSIDMOUNT_LENGTH);
}
#endif

#ifndef DISABLE_JUPYTERSIDMOUNT
/* We take first occurence of JUPYTERSIDMOUNT_HOME and JUPYTERSIDMOUNT_LENGTH from
 * 1. JUPYTERSIDMOUNT_HOME and JUPYTERSIDMOUNT_LENGTH environment
 * 2. jupytersidmount_home and SITE->jupytersidmount_length in (.ini) configuration file
 * 3. JUPYTERSIDMOUNT_HOME and JUPYTERSIDMOUNT_LENGTH compile time values
 * 4. hard-coded defaults here
 */
static const char *get_jupytersidmount_home()
{
    return get_runtime_var("JUPYTERSIDMOUNT_HOME", "jupytersidmount_home",
                           JUPYTERSIDMOUNT_HOME);
}

static int get_jupytersidmount_length()
{
    return get_runtime_var_int("JUPYTERSIDMOUNT_LENGTH",
                               "site->jupytersidmount_length",
                               JUPYTERSIDMOUNT_LENGTH);
}
#endif

/* username input validation using username_regex and length helpers */
static int validate_username(const char *username)
{
    WRITELOGMESSAGE(LOG_DEBUG, "Validate username '%s'\n", username);
    if (strlen(username) < USERNAME_MIN_LENGTH) {
        WRITELOGMESSAGE(LOG_DEBUG,
                        "Invalid username %s - too short (<%d)\n",
                        username, USERNAME_MIN_LENGTH);
        return 1;
    } else if (strlen(username) > USERNAME_MAX_LENGTH) {
        WRITELOGMESSAGE(LOG_DEBUG,
                        "Invalid username %s - too long (>%d)\n",
                        username, USERNAME_MAX_LENGTH);
        return 2;
    }

    WRITELOGMESSAGE(LOG_DEBUG, "Validated length of username '%s'\n", username);
    int retval;
    regex_t validator;
    int regex_res;
    const char *username_regex = get_username_regex();
    if (strlen(username_regex) < 2 || username_regex[0] != '^' ||
        username_regex[strlen(username_regex) - 1] != '$') {
        /* regex must have begin and end markers to avoid false hits */
        WRITELOGMESSAGE(LOG_ERR,
                        "Invalid username regex %s - line anchors required\n",
                        username_regex);
        return 3;

    }

    regex_res = regcomp(&validator, username_regex, REG_EXTENDED | REG_NOSUB);
    if (regex_res) {
        if (regex_res == REG_ESPACE) {
            WRITELOGMESSAGE(LOG_ERR,
                            "Memory error in username validation: %s\n",
                            strerror(ENOMEM));
            retval = 4;
        } else {
            WRITELOGMESSAGE(LOG_ERR,
                            "Syntax error in username_regex: %s\n",
                            username_regex);
            retval = 5;
        }
        return retval;
    }
    WRITELOGMESSAGE(LOG_DEBUG, "Validate username '%s' vs regex '%s'\n",
                    username, username_regex);
    /* Do not try to do submatch on group (last three arguments) */
    regex_res = regexec(&validator, username, 0, NULL, 0);
    if (regex_res == 0) {
        /* Success - username matches regex and length limits */
        WRITELOGMESSAGE(LOG_DEBUG,
                        "Validated username '%s' vs regex '%s'\n",
                        username, username_regex);
        retval = 0;
    } else if (regex_res == REG_NOMATCH) {
        WRITELOGMESSAGE(LOG_DEBUG,
                        "username %s did not match username_regex %s\n",
                        username, username_regex);
        retval = 6;
    } else {
        WRITELOGMESSAGE(LOG_ERR,
                        "Error in regexec: %zd\n",
                        regerror(regex_res, &validator, NULL, 0));
        retval = 7;
    }
    regfree(&validator);
    WRITELOGMESSAGE(LOG_DEBUG, "Validate username %s returning %d\n",
                    username, retval);
    return retval;
}

/* change uid and gid to MiG user */
static void chuser_mig()
{
#ifdef DEBUG
    int org_uid = getuid();
    int org_gid = getgid();
#endif                          /* DEBUG */
    setgid(MIG_GID);
    setuid(MIG_UID);
#ifdef DEBUG
    WRITELOGMESSAGE(LOG_DEBUG, "Changed uid: %d -> %d, gid: %d -> %d\n",
                    org_uid, getuid(), org_gid, getgid());
#endif                          /* DEBUG */
}

#endif                          /* _MIGAUTH_H_ */
