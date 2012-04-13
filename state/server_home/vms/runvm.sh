#!/bin/bash
#
# Script to manage the execution time of the virtual machine.
#
# Arguments:
# 1 = Virtual Machine Name
# 2 = Execution time
#

VBOX_STATE=0
VM_NAME=$1
EXEC_TIME=$2
VBoxHeadless -startvm "$VM_NAME" &
VBOX_PID=$!

while [ $VBOX_STATE -eq 0 ]
do

  # Progressively harder stop attempts on time out
  if [ $EXEC_TIME -lt -1 ]
  then
    echo "vm $VM_NAME with pid $VBOX_PID still running: giving up"
    break
  elif [ $EXEC_TIME -lt 0 ]
  then
    echo "vm $VM_NAME with pid $VBOX_PID still running: hard kill"
    kill -9 $VBOX_PID
  elif [ $EXEC_TIME -lt 1 ]
  then
    echo "vm $VM_NAME with pid $VBOX_PID still running: hard power off"
    VBoxManage -q controlvm "$VM_NAME" poweroff
  elif [ $EXEC_TIME -lt 2 ]
  then
    echo "vm $VM_NAME with pid $VBOX_PID timed out: soft power off"
    VBoxManage -q controlvm "$VM_NAME" acpipowerbutton
    # give it a little time to shut down cleanly
    sleep 15
  fi

  # Decrease exec time
  ((EXEC_TIME--))

  sleep 1

  if kill -0 $VBOX_PID 2> /dev/null      # Is the process still alive?
  then
    VBOX_STATE=0 # Yes
  else
    VBOX_STATE=1 # No
  fi

done

echo "CP: $VBOX_PID CS: $VBOX_STATE ET: $EXEC_TIME"
