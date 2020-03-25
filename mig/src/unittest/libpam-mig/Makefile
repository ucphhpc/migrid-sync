# Makefile for pam-mig unittests

### Start MiG site variables
# You can leave MIG_DEFAULTS like this to read the values dynamically from
# your MiGserver.conf (or $MIG_CONF if set in service environment).
# If on the other hand you define the values here the PAM module will save a
# bit of time on each login, since it doesn't have to look them up in the file.
# In any case you can always override the values at runtime by setting the same
# environment variables when running sshd or whichever service you use the PAM
# module in.

# Leave like this to use module defaults - likely won't fit your installation!
#MIG_DEFAULTS=
# TODO: implement this conf lookup!!
# Leave like this to lookup values in $MIG_CONF or default MiGserver.conf .
#MIG_DEFAULTS=-D'SHARELINK_HOME=""' -D'SHARELINK_LENGTH=-1' -D'USERNAME_REGEX=""'
# ... or hard code to your site values like this (NOTE: escaped dollar = '$$')
MIG_DEFAULTS=-D'MIG_UID=501' \
			 -D'MIG_GID=501' \
			 -D'RATE_LIMIT_EXPIRE_DELAY=300' \
			 -D'JOBSIDMOUNT_HOME="/home/mig/state/webserver_home"' \
			 -D'JOBSIDMOUNT_LENGTH=64' \
			 -D'JUPYTERSIDMOUNT_HOME="/home/mig/state/sessid_to_jupyter_mount_link_home"' \
			 -D'JUPYTERSIDMOUNT_LENGTH=64' \
			 -D'PASSWORD_MIN_LENGTH=8' \
			 -D'PASSWORD_MIN_CLASSES=3' \
			 -D'SHARELINK_HOME="/home/mig/state/sharelink_home"' \
			 -D'SHARELINK_LENGTH=10' \
			 -D'USERNAME_REGEX="^[a-zA-Z0-9][a-zA-Z0-9.@_-]{0,127}$$"'
### End of MiG site variables

#### Start of compiler configuration section ### 

DEBUG_DEFINES=-D'DEBUG'
DEBUG_CFLAGS=-g

CC = gcc
INCLUDES=-I./ -I/usr/include/python2.7
DEFINES=$(DEBUG_DEFINES) \
		$(MIG_DEFAULTS)
CFLAGS=${DEBUG_CFLAGS} \
	   -Wall
	   #-Wpedantic
LDFLAGS= -lpython2.7 -ldl

#### End of compiler configuration section ###

all:	unittest_migauthhandler

#%.o:	%.c
#	${CC} -std=gnu99 ${INCLUDES} ${MIG_DEFAULTS} -fPIC -Wall -Wpedantic -c $< -o $@

unittest_migauthhandler:	unittest_migauthhandler.c migauth.h  migauthhandler.c
	${CC} -std=gnu99 ${INCLUDES} ${DEFINES} -D'DEBUG_LOG_STDERR' ${CFLAGS} -o $@ $< ${LDFLAGS} 
	
clean:
	rm -f unittest_migauthhandler
	rm -f build-stamp
