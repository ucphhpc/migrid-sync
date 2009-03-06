#!/bin/bash
MIG_USER="mig_sss"

pgid_list=`ps -u $MIG_USER -o pgid=`
count=0
for i in $pgid_list; do
  if [ $i -eq $1 ]; then
     count="$[$count+1]"
  fi
done
echo $count      
