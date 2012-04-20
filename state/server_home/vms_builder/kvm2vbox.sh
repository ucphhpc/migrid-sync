#!/bin/bash
#
# Convert qcow2 images in 
#  kvm-os-images-*/
# to vmdk images in corresponding
#  vbox3.1-os-images-*/

sync
for src in kvm-os-images-*/*.qcow2; do
	srcdir=$(dirname $src)
	dstdir=$(echo $srcdir|sed 's/kvm/vbox3.1/g')
	img=$(basename $src)
	name=$(echo $img|sed 's/.qcow2//g')
	dst=$dstdir/$name.vmdk
	mkdir -p $dstdir
	if [ ! -e "$dst" -o "$dst" -ot "$src" ]; then
		echo "convert $src to $dst"
		qemu-img convert -f qcow2 -O vmdk $src $dst
	else
		echo "seems $src was already converted to $dst"
	fi
done
sync
