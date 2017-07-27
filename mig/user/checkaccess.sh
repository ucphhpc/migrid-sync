#!/bin/bash
#
# Check that expected access restrictions apply - highly specific to server
# and my user.
#
# Run with something like
# ./checkaccess.sh $(egrep '^password ' ~/.mig/miguser.conf|awk '{print $2; }')

KEYPATH=$HOME/.mig/key.pem
CERTPATH=$HOME/.mig/cert.pem
PW=$1
CURL="curl"
#CURLOPTS="--location --fail --silent  --show-error"
CURLCERTOPTS="--location --fail --silent --output /dev/null"
CURLOIDOPTS="--location --fail --silent --output /dev/null --write-out %{url_effective}"
CURLAUTH="--cert $CERTPATH --key $KEYPATH --pass $PW"

check_cert_valid() {
    TARGET="$1"
    for BASEURL in 'https://dk-cert.migrid.org/cert_redirect/' \
		       'https://dk-cert.migrid.org/+C=DK+ST=NA+L=NA+O=NBI+OU=NA+CN=Jonas_Bardino+emailAddress=bardino@nbi.ku.dk/' ; do
	URL="${BASEURL}${TARGET}"
	$CURL $CURLCERTOPTS $CURLAUTH "$URL" || echo "MISSING ACCESS TO $URL!"
    done
}

check_cert_invalid() {
    TARGET="$1"
    # Access to cert vhost without cert
    for BASEURL in 'https://dk-cert.migrid.org/cert_redirect/' \
		       'https://dk-cert.migrid.org/+C=DK+ST=NA+L=NA+O=NBI+OU=NA+CN=Jonas_Bardino+emailAddress=bardino@nbi.ku.dk/'; do
	URL="${BASEURL}${TARGET}"
	$CURL $CURLCERTOPTS "$URL" && echo "ILLEGAL ACCESS TO $URL!"
    done
    # Out of bounds for cert
    for BASEURL in 'https://dk-cert.migrid.org/+C=DK+ST=NA+L=NA+O=NBI+OU=NA+CN=Martin_Rehr+emailAddress=rehr@nbi.ku.dk/' ; do
	URL="${BASEURL}${TARGET}"
	$CURL $CURLCERTOPTS $CURLAUTH "$URL" && echo "ILLEGAL ACCESS TO $URL!"
    done
    # Access to oid vhost with or without cert
    for BASEURL in 'https://dk-ext.migrid.org/cert_redirect/' \
		       'https://dk-ext.migrid.org/+C=DK+ST=NA+L=NA+O=NBI+OU=NA+CN=Jonas_Bardino+emailAddress=bardino@nbi.ku.dk/'; do
	URL="${BASEURL}${TARGET}"
	# This may result in either redirect to openid and success or direct fail with forbidden
	OUT=$($CURL $CURLOIDOPTS "$URL")
	[ $? -eq 0 ] && (echo $OUT | grep -q openid || echo "ILLEGAL ACCESS TO $URL!")
	OUT=$($CURL $CURLOIDOPTS $CURLAUTH "$URL")
	[ $? -eq 0 ] && (echo $OUT | grep -q openid || echo "ILLEGAL CERT ACCESS TO $URL!")
    done
}


echo "= Running tests with expected access denial ="
echo ""
TARGET="welcome.txt"
echo "== $TARGET =="
check_cert_invalid $TARGET

echo ""
TARGET="seafile_readonly/14b108dc-4b4f-406c-a03e-40fa3463ef67_shared/test-sync.txt"
echo "== $TARGET =="
check_cert_invalid $TARGET

echo ""
TARGET="P-Cubed/README"
echo "== $TARGET =="
check_cert_invalid $TARGET

echo ""
TARGET="vgrid_shared/P-Cubed/.vgridtracker/wsgi-bin/trac.wsgi"
echo "== $TARGET =="
check_cert_invalid $TARGET

echo ""
TARGET=".htaccess"
echo "== $TARGET =="
check_cert_valid $TARGET | grep -q "MISSING ACCESS" || echo "ILLEGAL ACCESS TO $TARGET"

echo ""
TARGET="../../mig/server/MiGserver.conf"
echo "== $TARGET =="
check_cert_valid $TARGET | grep -q "MISSING ACCESS" || echo "ILLEGAL ACCESS TO $TARGET"


echo ""
echo "= Running tests with expected access granted ="
echo ""
TARGET="welcome.txt"
echo "== $TARGET =="
check_cert_valid $TARGET

echo ""
TARGET="seafile_readonly/14b108dc-4b4f-406c-a03e-40fa3463ef67_shared/test-sync.txt"
echo "== $TARGET =="
check_cert_valid $TARGET

echo ""
TARGET="P-Cubed/README"
echo "== $TARGET =="
check_cert_valid $TARGET

echo ""
TARGET="vgrid_shared/P-Cubed/.vgridtracker/wsgi-bin/trac.wsgi"
echo "== $TARGET =="
check_cert_valid $TARGET

echo ""
