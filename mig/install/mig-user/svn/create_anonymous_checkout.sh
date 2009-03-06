#!/bin/bash -e
#
# Create a limited MiG checkout excluding sensible date like yet to 
# be published material
#

MODULE="mig"
TAG=""
TAG_OPT=""
DIR="$MODULE"
PUBLIC="$HOME/public/"
SVNOPTS=""
SVN="/usr/bin/svn" 
TAR="/bin/tar"
SVNROOT="svn+ssh://amigos18.diku.dk/home/subversion"
PROJECT="project_MiG-server"

function restricted_copy() {
    EXCLUDE_LIST=".svn thesis doc private-doc apache install certs wwwserver wwwpublic"
    INPUT_BASE="$1"
    OUTPUT_BASE="$2"
    TODAY=`date "+%d%m%y"`
    TAR_PATH="$2/mig-svn${TODAY}.tar.gz"
    EXCLUDES=""
    for name in $EXCLUDE_LIST; do
	EXCLUDES="--exclude=$name $EXCLUDES"
    done
    echo
    echo "Creating limited version of svn checkout:"
    umask 022
    $TAR $EXCLUDES -c -z -f $TAR_PATH $INPUT_BASE
    $TAR -C $OUTPUT_BASE -x -z -f $TAR_PATH
    chmod -R o+r $OUTPUT_BASE/*
    chmod 755 $OUTPUT_BASE/*
}

### Main ###
if [ $# -gt 0 ]; then
	SVNROOT="${1}@${SVNROOT}"
fi
if [ $# -gt 1 ]; then
	TAG="$2"
	TAG_OPT="-r$TAG"
	DIR="$MODULE-$TAG"
fi

echo $SVNROOT
# Create a private updated version of the module
# Don't worry about permissions as we're inside a private dir
if [ -d $DIR ]; then
	echo "Updating $DIR:"
	$SVN -q update $TAG_OPT $DIR
else
	echo "Creating Checkout:"
	SVNOPTS="$SVNOPTS $TAG_OPT"
	$SVN -q checkout $SVNOPTS $SVNROOT/$PROJECT/trunk $MODULE 
fi

mkdir -p $PUBLIC
restricted_copy $DIR $PUBLIC

exit 0
