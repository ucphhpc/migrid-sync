#!/bin/bash
#
# Update repo with all packages in this directory and subdirs

ARCHITECTURES="i386 amd64"
DIST="dists/stable"
SECTION="main"
POOL_DIR="pool/${SECTION}"
SOURCE_DIR="${DIST}/${SECTION}/source"

echo '= Scanning binaries ='
for ARCH in $ARCHITECTURES; do
        BINARY_DIR="${DIST}/${SECTION}/binary-${ARCH}"
        dpkg-scanpackages ${POOL_DIR} /dev/null | gzip -9c > ${BINARY_DIR}/Packages.gz
	#gunzip -c ${BINARY_DIR}/Packages.gz > ${BINARY_DIR}/Packages
done

echo '= Scanning sources ='
#dpkg-scansources --debug ${POOL_DIR} /dev/null
dpkg-scansources ${POOL_DIR} /dev/null | gzip -9c > ${SOURCE_DIR}/Sources.gz

echo '= Updating repo index ='
rm -f  ${DIST}/Release.gpg
apt-ftparchive -o APT::FTPArchive::Release::Origin='Minimum intrusion Grid' -o APT::FTPArchive::Release::Label='MiG' -o APT::FTPArchive::Release::Suite='stable' -o APT::FTPArchive::Release::Codename='stable' -o APT::FTPArchive::Release::Architectures="${ARCHITECTURES}" -o APT::FTPArchive::Release::Components='main stable' release . > ${DIST}/Release
echo ''
echo '= Signing repo index with MiG signing key ='
echo '... the passphrase is included in the MiG developers VGrid SCM'
echo ''
EMAIL='MiG signing key <mig@www.migrid.org>' gpg -abs -o ${DIST}/Release.gpg ${DIST}/Release
