#!/bin/bash
#
# Update repo with all packages in this directory and subdirs

ARCHITECTURES="i386 amd64"
DIST="dists/stable"
SECTION="main"
POOL_DIR="pool/${SECTION}"
SOURCE_DIR="${DIST}/${SECTION}/source"

# Skip apt-ftparchive commands if not available so that signing can be done locally
# after running this script over sshfs from a Debian/Ubuntu host woth apt-ftparchive  
APTFTPARCHIVE=/usr/bin/apt-ftparchive

echo '= Scanning binaries ='
for ARCH in $ARCHITECTURES; do
        BINARY_DIR="${DIST}/${SECTION}/binary-${ARCH}"
	mkdir -p $BINARY_DIR
	if [ -x $APTFTPARCHIVE ]; then
		$APTFTPARCHIVE -o APT::FTPArchive::Release::Origin='Minimum intrusion Grid' -o APT::FTPArchive::Release::Label='MiG' -o APT::FTPArchive::Release::Suite='stable' -o APT::FTPArchive::Release::Codename='stable' -o APT::FTPArchive::Release::Architectures="${ARCHITECTURES}" -o APT::FTPArchive::Release::Components='main stable' packages ${POOL_DIR} | gzip -9c > ${BINARY_DIR}/Packages.gz
		gunzip -c ${BINARY_DIR}/Packages.gz > ${BINARY_DIR}/Packages
	fi
done

echo '= Scanning sources ='
mkdir -p $SOURCE_DIR
if [ -x $APTFTPARCHIVE ]; then
	$APTFTPARCHIVE -o APT::FTPArchive::Release::Origin='Minimum intrusion Grid' -o APT::FTPArchive::Release::Label='MiG' -o APT::FTPArchive::Release::Suite='stable' -o APT::FTPArchive::Release::Codename='stable' -o APT::FTPArchive::Release::Architectures="${ARCHITECTURES}" -o APT::FTPArchive::Release::Components='main stable' sources ${POOL_DIR} | gzip -9c > ${SOURCE_DIR}/Sources.gz
	gunzip -c ${SOURCE_DIR}/Sources.gz > ${SOURCE_DIR}/Sources
fi

echo '= Updating repo index ='
rm -f  ${DIST}/Release.gpg
if [ -x $APTFTPARCHIVE ]; then
	(cd ${DIST} && $APTFTPARCHIVE -o APT::FTPArchive::Release::Origin='Minimum intrusion Grid' -o APT::FTPArchive::Release::Label='MiG' -o APT::FTPArchive::Release::Suite='stable' -o APT::FTPArchive::Release::Codename='stable' -o APT::FTPArchive::Release::Architectures="${ARCHITECTURES}" -o APT::FTPArchive::Release::Components='main stable' release . > Release)
fi
echo ''
echo '= Signing repo index with MiG signing key ='
echo '... the passphrase is included in the MiG developers VGrid SCM'
echo ''
EMAIL='Minimun intrusion Grid <mig@migrid.org>' gpg -abs -o ${DIST}/Release.gpg ${DIST}/Release
