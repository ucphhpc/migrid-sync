#!/bin/bash
#
# Build all our images for kvm and vbox31
# ubuntu dist and arch combinations can be overridden on the command line

if [ $# -lt 2 ]; then
	echo "Usage: $0 mig_shared_dir mig_state_vms_builder_dir [dists] [archs]"
	echo "Where the optional dists argument is a string listing Ubuntu"
	echo "dist names separated by space."
	echo "archs is a single string with architecture names separated by a" 
	echo "space."
	echo "Example to build 32 and 64 bit images for lucid and precise:"
	echo "$0 $HOME/mig/shared $HOME/mig/state/server_files/vms_builder \\"
	echo "		'lucid precise' 'i386 amd64'"
	exit 1
fi

# Change run to 'echo' to only show commands for partial manual runs
#run='echo'
run=''

flavorlist=("lucid" "precise")
archlist=("i386" "amd64")
labellist=("basic" "escience-base" "escience-astro")
cwd=$PWD
shared_dir="$1"
builder_dir=$2
if [ $# -ge 3 ]; then
	flavorlist=($(echo $3))
fi
if [ $# -ge 4 ]; then
	archlist=($(echo $4))
fi
if [ $# -ge 5 ]; then
	labellist=($(echo $5))
fi


lookup_version() {
	flavors=('lucid' 'maverick' 'natty' 'oneiric' 'precise')
	versions=('10.04' '10.10' '11.04' '11.10' '12.04')
	count=${#flavors[@]}
	index=0
	name="$1"
	while [ "$index" -lt "$count" ]; do
		cur="${flavors[$index]}"
		if [ "$name" = "$cur" ]; then
			version="${versions[$index]}"
			#echo  "found version: $version"
			break
		fi
		let "index++"
	done
	export version
}

for flavor in ${flavorlist[@]}; do
	# lookup version number from flavor
	flavorindex=0
	version=''
	lookup_version $flavor
	# apt-proxy hogs memory - restart to free it once in a while
	sudo service apt-proxy restart
	for arch in ${archlist[@]}; do
	    for label in ${labellist[@]}; do
		if [ "$label" = "basic" ]; then
			extras=""
		elif [ "$label" = "escience-base" ]; then
			extras="libatlas3gf-base python-scipy \
				python-matplotlib ipython python-imaging \
				python-pip"
		elif [ "$label" = "escience-astro" ]; then
			# TODO: add mysql python-pywcs stsci_python where available
			# python-pywcs is available in precise and on this PPA
			# https://launchpad.net/~olebole/+archive/astro
			extras="libatlas3gf-base python-scipy \
				python-matplotlib ipython python-imaging \
				python-pip sqlite3 python-sqlalchemy \
				python-pyfits"
		else
			echo "skipping unknown label: $label"
		fi
		$run echo "build ubuntu $flavor $label image for $arch"
		$run cd $shared_dir
		$run python vmbuilder.py --suite=$flavor --hypervisor=kvm \
			--vmbuilder-opts='' --architecture=$arch $extras
		$run cd $builder_dir
		$run ./tmp2kvm.sh $arch $label $version $flavor
	    done
	done
done

# Convert all images to vbox31 format
$run cd $builder_dir
$run ./kvm2vbox.sh

# Copy all data images to separate dirs for flexible packaging
$run cd $builder_dir
$run ./clonedataimg.sh

$run cd $cwd
exit 0
