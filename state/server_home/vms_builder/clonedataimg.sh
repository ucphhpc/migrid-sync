#!/bin/bash
#
# Copies qcow2 and vmdk data images in 
#  *-os-images-*/*-data.*
# to corresponding separate data image dirs
#  *-data-images-*/

# Change run to 'echo' to only show commands for partial manual runs
#run='echo'
run=''

$run sync
for src in {kvm,vbox3.1}-os-images-*-pristine/*-data.*; do
	srcdir=$(dirname $src)
	dstdir=$(echo $srcdir|sed 's/-os-/-data-/g')
	img=$(basename $src)
	dst=$dstdir/$img
	$run mkdir -p $dstdir
	if [ ! -e "$dst" -o "$dst" -ot "$src" ]; then
		$run echo "copy $src to $dst"
		$run cp $src $dst
	else
		$run echo "seems $src was already copied to $dst"
	fi
done
$run sync
