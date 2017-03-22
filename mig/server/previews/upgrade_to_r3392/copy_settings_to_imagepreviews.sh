#!/bin/bash

# Copy settings.h5 to imagepreviews.h5

SETTINGS_LIST="settings.h5.list.txt"

IFS=$'\n'
vgrid_list=()
rule_list=()
for settings_file in `cat ${SETTINGS_LIST}`; do
    new_file=`echo ${settings_file} | sed s:/.meta/settings.h5:/.meta/imagepreviews.h5:g`
    command="cp -f \"${settings_file}\" \"${new_file}\""
    echo ${command}
    eval $command
done
