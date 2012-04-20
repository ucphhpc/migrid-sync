#!/bin/bash
#
# Rename tmp build files from
#   kvm-ubuntu-*/
# to labelled images in
#   kvm-os-images-*

ARCH="i386"
if [ $# -ge 1 ]; then
    ARCH="$1"
fi
FLAVOR="basic"
if [ $# -ge 2 ]; then
    FLAVOR="$2"
fi
VERSION="10.04"
if [ $# -ge 3 ]; then
    VERSION="$3"
fi
CODENAME="lucid"
if [ $# -ge 4 ]; then
    CODENAME="$4"
fi

YEAR="20$(echo $VERSION|cut -f1 -d.)"
export ARCH
export CODENAME

srcdir="kvm-ubuntu-$CODENAME-$ARCH"
dstdir="kvm-os-images-$YEAR-1"
mkdir -p $dstdir
sync

files=($(ls -S $srcdir))
echo "DEBUG: files: ${files[@]}"
if [ ${#files[@]} -lt 3 ]; then
	echo "no source files to move from $srcdir"
	exit 0
fi

syssrc="$srcdir/${files[0]}"
datasrc="$srcdir/${files[1]}"
runsrc="$srcdir/${files[2]}"
sysdst="$dstdir/ubuntu-$VERSION-$ARCH-$FLAVOR.qcow2"
datadst="$dstdir/ubuntu-$VERSION-$ARCH-data.qcow2"
rundst="$dstdir/run-ubuntu-$VERSION-$ARCH-$FLAVOR.sh"
[ -e "$syssrc" ] && rsync -aP "$syssrc" "$sysdst"
[ -e "$datasrc" ] && rsync -aP "$datasrc" "$datadst"
[ -e "$runsrc" ] && rsync -aP "$runsrc" "$rundst"
sync

