#! /bin/bash
#
# start script for MiG daemons.  Hacks around the problem that MiG
# needs to start in a certain directory structure
#
#######################################

MIG_PATH=${1:-/opt/mig}

cd $MIG_PATH/mig/server
./grid_script.py 2>&1 > $MIG_PATH/scriptdaemon.log &
./grid_monitor.py 2>&1 > $MIG_PATH/monidaemon.log &
exit 0
