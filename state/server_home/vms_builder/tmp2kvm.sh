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

# Change run to 'echo' to only show commands for partial manual runs
#run='echo'
run=''

srcdir="kvm-ubuntu-$CODENAME-$ARCH"
dstdir="kvm-os-images-$YEAR-1"
$run mkdir -p $dstdir
$run sync

files=($(ls -S $srcdir))
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
if [ -e "$syssrc" ]; then
	$run rsync -aP "$syssrc" "$sysdst"
	$run rm -f "$syssrc"
fi
if [ -e "$datasrc" ]; then
	$run rsync -aP "$datasrc" "$datadst"
	$run rm -f "$datasrc"
fi
if [ -e "$runsrc" ]; then
	$run rsync -aP "$runsrc" "$rundst"
	$run rm -f "$runsrc"
fi
$run sync

