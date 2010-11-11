#!/bin/bash
#
# Generate temporary key without passphrase and keep it only as long as proxy runs

make_key() {
    inpath=$1
    outpath=$2
    echo "creating temporary key in $outpath"
    openssl rsa -in $inpath -out $outpath
    chmod 600 $outpath
}

remove_key() {
    path=$1
    echo "cleaning up temporary key in $path"
    rm -f $path
}

make_key ~/.mig/key.pem ~/.mig/tmp.pem
python migproxy.py
remove_key ~/.mig/tmp.pem
