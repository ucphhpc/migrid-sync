# Makefile for libnss-mig

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
#MIG_DEFAULTS=-D'SHARELINK_HOME="/home/mig/state/sharelink_home"' -D'SHARELINK_LENGTH=10' -D'USERNAME_REGEX="^[a-zA-Z][a-zA-Z0-9\.@_-]{0,127}$"'

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

sysconfdir = /etc

# mandir = /usr/local/src/less-394/debian/less/usr/share/man
manext = 1
manprefix =

#### End of system configuration section. ####

all:	libnss_mig

libnss_mig:	libnss_mig.c
	${CC} -std=gnu99 -fPIC ${MIG_DEFAULTS} -Wall -Wpedantic -shared -o libnss_mig.so.2 -Wl,-soname,libnss_mig.so.2 libnss_mig.c #-lini_config

install:	libnss_mig.so.2
	# remember  /lib64/libnss_mig.so.2 -> libnss_mig-2.3.6.so
	${INSTALL_DATA} libnss_mig.so.2 ${prefix}/lib64/libnss_mig-2.3.6.so
	cd ${prefix}/lib64 && ln -fs libnss_mig-2.3.6.so libnss_mig.so.2

clean:
	rm -f libnss_mig.so.2
	rm -f build-stamp
