#!/bin/bash
# 
# Run SCRIPT after distro installation finishes. Script will be called with
# the guest's chroot as first argument, so you can use 
# chroot $1 <cmd>
# to run code in the virtual machine.

# We need proc for network access during post install
mount --bind /proc $1/proc

# Prepare vbox guest additions for use in dynamic vnc proxy settings.
# We delay dkms module build until first boot for right kernel.
# Base build fails if aptitude is included early, so we install it here.
chroot $1 apt-get update
# Force noninteractive mode to avoid whiptail promts hanging install
export DEBIAN_FRONTEND=noninteractive
chroot $1 apt-get install -y aptitude
# Dkms only builds modules for kernels with available headers:
# Install 'virtual' headers to automatically pull in pae headers for i386
# and generic for other archs
chroot $1 aptitude install -y linux-headers-virtual
chroot $1 aptitude install -y -d virtualbox-ose-guest-x11
# Other delayed packages that break vmbuilder: missing icons and tools
chroot $1 aptitude install -y elementary-icon-theme xfce4-goodies
# Replace default gnome session with xfce
chroot $1 mv /usr/share/xsessions/gnome.desktop /usr/share/xsessions/gnome.desktop.old
chroot $1 ln -s /usr/share/xsessions/xfce.desktop /usr/share/xsessions/gnome.desktop

# Launch migvncproxy from GDM init to get vnc running at the right time
sed -ie 's/^exit 0//g' "$1/etc/gdm/Init/Default"
echo "/etc/init.d/migvncproxy start" >> $1/etc/gdm/Init/Default
echo "/etc/init.d/migjobmonitor start" >> $1/etc/gdm/Init/Default
echo "" >> $1/etc/gdm/Init/Default
echo "exit 0" >> $1/etc/gdm/Init/Default


# Remove temporary proc access again
umount $1/proc

exit 0
