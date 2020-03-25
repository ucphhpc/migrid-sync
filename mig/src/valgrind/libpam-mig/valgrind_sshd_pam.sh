#!/bin/bash
BASEPATH="${PWD}"
logdir="${BASEPATH}/log"
program="/usr/sbin/sshd -D -f /etc/ssh/sshd_config-MiG-sftp-subsys"
datestamp=$(date +%Y-%m-%d_%T)
logfile="${logdir}/${datestamp}.valgrind"
dlopen_supp="${BASEPATH}/valgrind-dlfcn.supp"
pyinit_supp="${BASEPATH}/valgrind-c-python-api.supp"
pymig_supp="${BASEPATH}/valgrind-c-python-api-mig.supp"
sshdpam_supp="${BASEPATH}/valgrind-sshd-pam.supp"
pammig_supp="${BASEPATH}/valgrind-pam-mig.supp"

valgrind_cmd="valgrind --tool=memcheck \
			    --trace-children=yes \
			    --dsymutil=yes \
			    --leak-check=full \
			    --show-leak-kinds=all \
			    --suppressions=${dlopen_supp} \
			    --suppressions=${pyinit_supp} \
			    --suppressions=${pymig_supp} \
			    --suppressions=${sshdpam_supp} \
			    --suppressions=${pammig_supp} \
			    --gen-suppressions=all \
			    --log-file=${logfile} \
			    ${program}"
echo "Output to file: ${logfile}"
mkdir -p ${logdir}
echo ${valgrind_cmd}
eval ${valgrind_cmd}
