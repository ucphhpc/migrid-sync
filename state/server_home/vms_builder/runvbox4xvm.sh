#!/bin/bash
#
# Script to manage the execution time of the virtual machine.
#
# Requires VBOXHEADLESS and VBOXMANAGE environments to point to the
# VBoxHeadless and VBoxManage binaries respectively.
# They are automatically set by the VIRTUALBOX-*-1 runtime environments
#
# Arguments:
# 1 = Virtual Machine Name
# 2 = Execution time
# Optional arguments:
# 3 = Screen width
# 4 = Screen height
# 5 = Screen bits per pixel

VBOX_STATE=0
VM_NAME=$1
EXEC_TIME=$2
VM_XRES=1024
VM_YRES=768
VM_BPP=24
if [ $# -ge 3 ]; then
    VM_XRES=$3
fi
if [ $# -ge 4 ]; then
    VM_YRES=$4
fi
if [ $# -ge 5 ]; then
    VM_BPP=$5
fi

$VBOXHEADLESS -startvm "$VM_NAME" &
VBOX_PID=$!

# Change display size once the VM is started
sleep 5 && $VBOXMANAGE -q controlvm "$VM_NAME" \
                       setvideomodehint $VM_XRES $VM_YRES $VM_BPP &

while [ $VBOX_STATE -eq 0 ]
do

  # Check for stop requests from user through server (live I/O)
  if [ -e "${VM_NAME}.stop" ]
  then
    echo "vm $VM_NAME received stop request - force time out"
    EXEC_TIME=1
  fi
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
    $VBOXMANAGE -q controlvm "$VM_NAME" poweroff
    # give it a little time to shut down
    sleep 5
  elif [ $EXEC_TIME -lt 2 ]
  then
    echo "vm $VM_NAME with pid $VBOX_PID timed out: soft power off"
    $VBOXMANAGE -q controlvm "$VM_NAME" acpipowerbutton
    # give it a little time to shut down cleanly
    sleep 15
  elif [ -x "$VBOXMANAGE" ]
  then
      # Pass remaining time to guest
      $VBOXMANAGE -q guestproperty set "$VM_NAME" time_left $((EXEC_TIME-2))
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
