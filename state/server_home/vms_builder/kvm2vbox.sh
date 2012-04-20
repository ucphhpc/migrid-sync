#!/bin/bash
#
# Convert qcow2 images in 
#  kvm-os-images-*/
# to vmdk images in corresponding
#  vbox3.1-os-images-*/

# Change run to 'echo' to only show commands for partial manual runs
#run='echo'
run=''

$run sync
for src in kvm-os-images-*/*.qcow2; do
	srcdir=$(dirname $src)
	dstdir=$(echo $srcdir|sed 's/kvm/vbox3.1/g')
	img=$(basename $src)
	name=$(echo $img|sed 's/.qcow2//g')
	dst=$dstdir/$name.vmdk
	$run mkdir -p $dstdir
	if [ ! -e "$dst" -o "$dst" -ot "$src" ]; then
		$run echo "convert $src to $dst"
		$run qemu-img convert -f qcow2 -O vmdk $src $dst
	else
		$run echo "seems $src was already converted to $dst"
	fi
done
$run sync
