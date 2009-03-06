#!/bin/bash -e
#
# Create a limited MiG checkout excluding sensible date like yet to be published material
#

MODULE="mig"
TAG=""
TAG_OPT=""
DIR="$MODULE"
PUBLIC="../public/"
CVSOPTS=""
CVS="/usr/bin/cvs" 
TAR="/bin/tar"
CVSROOT="bach.imada.sdu.dk:/home/jones/cvs"

function restricted_copy() {
    EXCLUDE_LIST="CVS thesis doc private-doc misc apache install todo-list certs wwwserver wwwpublic"
    INPUT_BASE="$1"
    OUTPUT_BASE="$2"
    EXCLUDES=""
    for name in $EXCLUDE_LIST; do
	EXCLUDES="--exclude=$name $EXCLUDES"
    done
    echo
    echo "Creating limited version of cvs checkout:"
    umask 022
    $TAR $EXCLUDES -c -z -f - $INPUT_BASE | $TAR -C $OUTPUT_BASE -x -v -z -f -
    chmod -R o+r $OUTPUT_BASE/*
    chmod 755 $OUTPUT_BASE/*
}

### Main ###
if [ $# -gt 0 ]; then
	CVSROOT="${1}@${CVSROOT}"
fi
if [ $# -gt 1 ]; then
	TAG="$2"
	TAG_OPT="-r$TAG"
	DIR="$MODULE-$TAG"
fi

echo $CVSROOT
# Create a private updated version of the module
# Don't worry about permissions as we're inside a private dir
if [ -d $DIR ]; then
	echo "Updating $DIR:"
	cd $DIR 
	$CVS -d $CVSROOT -q update $TAG_OPT -d -A -P
	cd ..
else
	echo "Creating Checkout:"
	CVSOPTS="$CVSOPTS -d $DIR $TAG_OPT"
	$CVS -d $CVSROOT -q checkout $CVSOPTS $MODULE
fi

mkdir -p $PUBLIC
restricted_copy $DIR $PUBLIC

ln -f -s ../shared $PUBLIC/mig/server
ln -f -s ../shared $PUBLIC/mig/cgi-bin
ln -f -s ../cgi-bin $PUBLIC/mig/shared/cgibin

exit 0
