#!/bin/bash
# 
# Run SCRIPT after distro installation finishes. Script will be called with
# the guest's chroot as first argument, so you can use 
# chroot $1 <cmd>
# to run code in the virtual machine.

# We need proc for network access during post install
mount --bind /proc $1/proc

# prepare vbox guest additions for use in dynamic vnc proxy settings
# we delay dkms module build until first boot for right kernel
chroot $1 aptitude update
chroot $1 aptitude install -y linux-headers-generic-pae
chroot $1 aptitude install -y -d virtualbox-ose-guest-x11
# Replace default gnome session with xfce
chroot $1 mv /usr/share/xsessions/gnome.desktop /usr/share/xsessions/gnome.desktop.old
chroot $1 ln -s /usr/share/xsessions/xfce.desktop /usr/share/xsessions/gnome.desktop

# Remove temporary proc access again
umount $1/proc

exit 0
