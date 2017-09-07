# Makefile for libnss-mig

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
	${CC} -std=gnu99 -fPIC -Wall -shared -o libnss_mig.so.2 -Wl,-soname,libnss_mig.so.2 libnss_mig.c

install:	libnss_mig.so.2
	# remember  /lib64/libnss_mig.so.2 -> libnss_mig-2.3.6.so
	${INSTALL_DATA} libnss_mig.so.2 ${prefix}/lib64/libnss_mig-2.3.6.so
	cd ${prefix}/lib64 && ln -fs libnss_mig-2.3.6.so libnss_mig.so.2

clean:
	rm -f libnss_mig.so.2
	rm -f build-stamp
