# Makefile for paramiko


# PLATFORM is expected overridden on command line to be e.g. 'el9' for RHEL/Rocky 9
PLATFORM = UNKNOWN

PATCH = /usr/bin/patch
PARAMIKO_VERSION = $(shell python -c 'import paramiko; print(paramiko.__version__)')
SILENCE = ${CURDIR}/silence-scan-noise_python-paramiko-${PARAMIKO_VERSION}.${PLATFORM}_transport.py.diff

patch:	
	if [ -e ${SILENCE} ]; then cd / && ${PATCH} --batch -p 1 < ${SILENCE}; fi

unpatch:
	if [ -e ${SILENCE} ]; then cd / && ${PATCH} --batch -R -p 1 < ${SILENCE}; fi
