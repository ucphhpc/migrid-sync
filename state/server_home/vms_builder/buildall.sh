#!/bin/bash
#
# Build all our images for kvm and vbox31

if [ $# -lt 2 ]; then
	echo "Usage: $0 mig_shared_dir mig_state_vms_builder_dir"
	exit 1
fi

cwd=$PWD
shared_dir="$1"
builder_dir=$2

for flavor in lucid; do
	# lucid is 10.04
	version=10.04
	for arch in i386 amd64; do
		# basic image
		cd $shared_dir
		python vmbuilder.py --suite=$flavor --hypervisor=kvm \
			--vmbuilder-opts='' --architecture=$arch
		cd $builder_dir
		./tmp2kvm.sh $arch 'basic' $version $flavor
		# escience-base image
		cd $shared_dir
		python vmbuilder.py --suite=$flavor --hypervisor=kvm \
			--vmbuilder-opts='' --architecture=$arch \
			libatlas3gf-base python-scipy python-matplotlib \
			ipython
		cd $builder_dir
		./tmp2kvm.sh $arch 'escience-base' $version $flavor
	done
done

# Convert all images to vbox31 format
cd $builder_dir
./kvm2vbox.sh

cd $cwd
exit 0
