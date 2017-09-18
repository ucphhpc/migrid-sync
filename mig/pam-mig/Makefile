# Makefile for pam-mig

### Start MiG site variables
# You can leave MIG_DEFAULTS like this to read the values dynamically from
# your MiGserver.conf (or $MIG_CONF if set in service environment).
# If on the other hand you define the values here the PAM module will save a
# bit of time on each login, since it doesn't have to look them up in the file.
# In any case you can always override the values at runtime by setting the same
# environment variables when running sshd or whichever service you use the PAM
# module in.

# Leave like this to lookup values in $MIG_CONF or default MiGserver.conf .
MIG_DEFAULTS=-D'SHARELINK_HOME=""' -D'SHARELINK_LENGTH=-1' -D'USERNAME_REGEX=""' 
# ... or hard code to your site values like this 
#MIG_DEFAULTS=-D'SHARELINK_HOME="/home/mig/state/sharelink_home"' -D'SHARELINK_LENGTH=10' -D'USERNAME_REGEX="^[a-zA-Z][a-zA-Z0-9\.@_-]{0,64}$"'

### End of MiG site variables

#### Start of system configuration section. ####

CC = gcc
INSTALL = /usr/bin/install
INSTALL_PROGRAM = ${INSTALL}
INSTALL_DATA = ${INSTALL} -m 755

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
securitydir = /lib64/security
libdir = ${prefix}/${securitydir}
libprefix =

sysconfdir = /etc

manext = 1
manprefix =

#### End of system configuration section. ####

all:	libpam_mig

libpam_mig:	libpam_mig.c b64.c b64-decode.c base64.h
	${CC} -std=gnu99 -fPIC ${MIG_DEFAULTS} -Wall -Wpedantic -shared -o libpam_mig.so -Wl,-soname,libpam_mig.so libpam_mig.c #-lini_config

install:	libpam_mig.so
	${INSTALL_DATA} libpam_mig.so ${libdir}/pam_mig.so

clean:
	rm -f libpam_mig.so
	rm -f build-stamp
