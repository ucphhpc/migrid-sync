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

echo ''
echo '= IMPORTANT ='
echo 'Packages should similarly be locally built and signed with the same key.'
echo 'It can be used for that by mounting it on the build host during build:'
echo 'mkdir -p  ~/mnt/mig@distlab4'
echo 'sshfs mig@distlab4: ~/mnt/mig@distlab4  -o uid=$(id -u) -o gid=$(id -g)'
echo '[optionally fetch mig-user-scripts package source with apt-get source mig-user-scripts]'
echo 'cd /path/to/mig-user-scripts/package/source'
echo 'EMAIL="MiG signing key <mig@www.migrid.org>" dch -i'
echo '[edit changelog and save - possibly cd to new dir if it mentions rename]'
echo '[make your changes]'
echo 'GNUPGHOME=~/mnt/mig@distlab4/.gnupg dpkg-buildpackage -rfakeroot'
echo '[copy package files to ~/mnt/mig@distlab4/state/wwwpublic/deb/pool/main/]'
echo '[finally re-run this script]'
