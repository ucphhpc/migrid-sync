#!/bin/bash
FRONTEND="$1"
for i in `cat $FRONTEND`; do
    cmd="./clean_and_start_resource.py $FRONTEND $i"
    echo $cmd
    $cmd
done
