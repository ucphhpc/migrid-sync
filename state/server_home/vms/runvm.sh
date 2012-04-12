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

while [[ $VBOX_STATE -eq 0 && $EXEC_TIME -gt 0 ]]
do

  if kill -0 $VBOX_PID       # Is the process still alive?
  then
    VBOX_STATE=0 # Yes
  else
    VBOX_STATE=1 # No
  fi

  # Decrease exec time
  ((EXEC_TIME--))

  sleep 1

done

# If still running then turn it off
if [ $VBOX_STATE -eq 0 ]; then
VBoxManage controlvm "$VM_NAME" acpipowerbutton
fi

echo "CP: $VBOX_PID CS: $VBOX_STATE ET: $EXEC_TIME"
