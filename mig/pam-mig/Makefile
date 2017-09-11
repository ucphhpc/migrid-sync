# Makefile for pam-mig

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
	${CC} -std=gnu99 -fPIC -Wall -shared -o libpam_mig.so -Wl,-soname,libpam_mig.so libpam_mig.c 

install:	libpam_mig.so
	${INSTALL_DATA} libpam_mig.so ${libdir}/pam_mig.so

clean:
	rm -f libpam_mig.so
	rm -f build-stamp
