# Makefile for pam-mig

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
# NOTE: we looup UID and GID of 'mig' user to limit hard-coding but we may stil
#       need to update paths and even the user name if using custom install
MIG_DEFAULTS=-D'MIG_UID=$(shell id -u mig)' \
	-D'MIG_GID=$(shell id -g mig)' \
	-D'RATE_LIMIT_EXPIRE_DELAY=300' \
	-D'JOBSIDMOUNT_HOME="$(shell ~mig/mig/server/readconfval.py webserver_home)"' \
	-D'JOBSIDMOUNT_LENGTH=64' \
	-D'JUPYTERSIDMOUNT_HOME="$(shell ~mig/mig/server/readconfval.py sessid_to_jupyter_mount_link_home)"' \
	-D'JUPYTERSIDMOUNT_LENGTH=64' \
	-D'PASSWORD_MIN_LENGTH=8' \
	-D'PASSWORD_MIN_CLASSES=3' \
	-D'SHARELINK_HOME="$(shell ~mig/mig/server/readconfval.py sharelink_home)"' \
	-D'SHARELINK_LENGTH=10' \
	-D'USERNAME_REGEX="^[a-zA-Z0-9][a-zA-Z0-9.@_-]{0,127}$$"'
### End of MiG site variables

#### Start of compiler configuration section ### 

DEBUG_DEFINES=
DEBUG_CFLAGS=
#DEBUG_DEFINES=-D'DEBUG' -D'DEBUG_LOG_STDERR=1'
#DEBUG_CFLAGS=-g

# NOTE: decide underlying python version to use or use pythonN-config below
#PYTHON_VERSION = 3.6m
#PYTHON_VERSION = 2.7

CC = gcc
PYCONF = $(shell which python3-config || which python2-config)
#INCLUDES=-I./ -I/usr/include/python${PYTHON_VERSION}
#INCLUDES=-I/. -I$(shell ${PYCONF} --includes)
DEFINES=$(DEBUG_DEFINES) \
		$(MIG_DEFAULTS)
#CFLAGS=${DEBUG_CFLAGS} -Wall -Wpedantic
CFLAGS=${DEBUG_CFLAGS} $(shell ${PYCONF} --cflags)
#LDFLAGS= -shared -lpython${PYTHON_VERSION}
#LDFLAGS= -shared $(shell ${PYCONF} --libs)
LDFLAGS= -shared $(shell ${PYCONF} --ldflags)

#### End of compiler configuration section ###

#### Start of system configuration section. ####

INSTALL = /usr/bin/install
INSTALL_PROGRAM = ${INSTALL} -m 755
INSTALL_DATA = ${INSTALL} -m 644

prefix = ""
exec_prefix = ${prefix}

# Where the installed binary goes.
bindir = ${exec_prefix}/bin
binprefix =

# Where the installed library goes.
# On deb systems PAM modules are stored in /lib/x86_64-linux-gnu/security/
# On rpm systems PAM modules go into /lib64/security/
# If on other platforms override securitydir with:
# securitydir=/path/to/security make -e install
securitydir := $(shell dirname $(firstword $(wildcard /lib*/security/pam_*.so /lib/*-linux-gnu/security/pam_*.so)))
libdir = ${prefix}/${securitydir}
libprefix =

sysconfdir = /etc

manext = 1
manprefix =

#### End of system configuration section. ####

all:	libpam_mig.so

#%.o:	%.c
#	${CC} -std=gnu99 ${INCLUDES} ${MIG_DEFAULTS} -fPIC -Wall -Wpedantic -c $< -o $@

libpam_mig.so:	libpam_mig.c b64.c b64-decode.c base64.h migauthhandler.c
	${CC} -std=gnu99 -fPIC ${INCLUDES} ${DEFINES} ${CFLAGS} -o $@ $< ${LDFLAGS} 

install:	libpam_mig.so
	${INSTALL_DATA} libpam_mig.so ${libdir}/pam_mig.so

clean:
	rm -f libpam_mig.so
	rm -f build-stamp
