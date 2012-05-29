#!/bin/bash
#
# Build all our images for kvm and vbox31
# ubuntu dist and arch combinations can be overridden on the command line

if [ $# -lt 2 ]; then
	echo "Usage: $0 mig_shared_dir mig_state_vms_builder_dir [dists] [archs] [flavors]"
	echo "Where the optional dists argument is a string listing Ubuntu"
	echo "dist names separated by space."
	echo "archs is a single string with architecture names separated by a" 
	echo "space."
	echo "flavors is a single string with package flavor names separated by a" 
	echo "space."
	echo "Example to build all 32 and 64 bit images for lucid and precise:"
	echo "$0 $HOME/mig/shared $HOME/mig/state/server_files/vms_builder \\"
	echo "		'lucid precise' 'i386 amd64'"
	exit 1
fi

# Change run to 'echo' to only show commands for partial manual runs
#run='echo'
run=''

distlist=("lucid" "precise")
archlist=("i386" "amd64")
flavorlist=("basic" "escience-base" "escience-astro" "nemid-jail")
cwd=$PWD
diskdir="$HOME/.VirtualBox/HardDisks"
shared_dir="$1"
builder_dir=$2
if [ $# -ge 3 ]; then
	distlist=($(echo $3))
fi
if [ $# -ge 4 ]; then
	archlist=($(echo $4))
fi
if [ $# -ge 5 ]; then
	flavorlist=($(echo $5))
fi


lookup_version() {
	dists=('lucid' 'maverick' 'natty' 'oneiric' 'precise')
	versions=('10.04' '10.10' '11.04' '11.10' '12.04')
	years=('2010' '2010' '2011' '2011' '2012')
	count=${#dists[@]}
	index=0
	name="$1"
	while [ "$index" -lt "$count" ]; do
		cur="${dists[$index]}"
		if [ "$name" = "$cur" ]; then
			version="${versions[$index]}"
			year="${years[$index]}"
			#echo  "found version: $version"
			#echo  "found year: $year"
			break
		fi
		let "index++"
	done
	export version
	export year
}

for dist in ${distlist[@]}; do
	# lookup version number and year from dist 
	version=''
	year=''
	lookup_version $dist
	# apt-proxy hogs memory - restart to free it once in a while
	$run sudo service apt-proxy restart
	for arch in ${archlist[@]}; do
	    for flavor in ${flavorlist[@]}; do
		if [ "$flavor" = "basic" ]; then
			extras=""
		elif [ "$flavor" = "escience-base" ]; then
			extras="netsurf xfce4-goodies libatlas3gf-base \
				python-scipy python-matplotlib ipython \
				python-imaging python-pip"
		elif [ "$flavor" = "escience-astro" ]; then
			# TODO: add mysql python-pywcs stsci_python where available
			# python-pywcs is available in precise and on this PPA
			# https://launchpad.net/~olebole/+archive/astro
			extras="netsurf xfce4-goodies libatlas3gf-base \
				python-scipy python-matplotlib ipython \
				python-imaging python-pip sqlite3 \
				python-sqlalchemy python-pyfits"
		elif [ "$flavor" = "nemid-jail" ]; then
			extras="firefox icedtea-plugin"
		else
			echo "skipping unknown flavor: $flavor"
		fi
		echo "build ubuntu $dist $flavor image for $arch"
		$run cd $shared_dir
		$run python vmbuilder.py --suite=$dist --hypervisor=kvm \
			--vmbuilder-opts='' --architecture=$arch $extras
		$run cd $builder_dir
		$run ./tmp2kvm.sh $arch $flavor $version $dist
	    done
	done
done

# Convert all images to vbox31 format
$run cd $builder_dir
$run ./kvm2vbox.sh

# Copy all data images to separate dirs for flexible packaging
$run cd $builder_dir
$run ./clonedataimg.sh

echo "Pristine kvm and vbox images now available in the pristine dir(s):"
echo *-pristine
echo "Run the images once to install vbox guest additions and verify that
everything works as expected before release:"
echo "mkdir -p $diskdir"
for dist in ${distlist[@]}; do
	# lookup version number and year from dist
	version=''
	year=''
	lookup_version $dist
	for arch in ${archlist[@]}; do
	    for flavor in ${flavorlist[@]}; do
		osimg="ubuntu-$version-$arch-$flavor.vmdk"
		osdir="vbox3.1-os-images-$year-pristine"
		ossrc="$osdir/$osimg"
		releasedir="${osdir/-pristine/-1}"
		dataimg="${osimg/$flavor/data}"
		datadir="${osdir/-os-/-data-}"
		datasrc="$datadir/$dataimg"
		echo "rsync -aSP $ossrc $datasrc $diskdir/ && \\"
		echo "sync && \\"
		echo "vbox31-display.job $arch $flavor $version && \\"
		echo "mkdir -p $releasedir && \\"
		echo "sync && \\"
		echo "rsync -aSP $diskdir/$osimg $releasedir/"
	    done
	    # only copy data image once
	    echo "rsync -aSP $datasrc $releasedir/"
	done
done
echo "Checklist:"
echo " * job-dir mount"
echo " * vnc access"
echo " * flavor packages"

$run cd $cwd
exit 0
