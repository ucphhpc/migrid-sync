#!/bin/bash
#
# Traverse provided dir and generate a file with checksums for all files older
# than provided number of days. Useful in relation to backup verification.
#
# Example use:
# $0 /home/mig/state/user_home /home/mig/user-checksums.out 7 14

SCRIPTPATH=$(realpath $0)
SCRIPTNAME=$(basename $SCRIPTPATH)
CHKSUM="/usr/bin/sha256sum"

TARGETDIR="$1"
OUTPATH="$2"
MINDAYS="$3"
MAXDAYS="$4"

if [ $# -ne 4 ];then
    echo "USAGE: $SCRIPTNAME TARGETDIR OUTPATH MINDAYS MAXDAYS"
    exit 1
fi

if [ ! -d "$TARGETDIR" ]; then
    echo "No such target dir: $TARGETDIR"
    exit 1
fi

echo "=== Checksum files $MINDAYS to $MAXDAYS days old in $TARGETDIR ==="
{
    find ${TARGETDIR} -mindepth 1 -type f -ctime +${MINDAYS} -ctime -${MAXDAYS} \
        -exec  ${CHKSUM} \{\} \;
} > ${OUTPATH}
echo "Wrote checksums:"
echo "    $(wc -l $OUTPATH)"
