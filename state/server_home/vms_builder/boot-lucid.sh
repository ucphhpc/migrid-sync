#!/bin/bash
#
# Set up virtualbox guest additions and start MiG VNC proxy agent that relies
# on them for dynamic proxy settings

# TODO: this is still not optimal with rc.local happening after gdm launch

echo ""
echo " * Installing guest additions"
# We delay module install until this point to make sure we are running the
# right kernel
aptitude install -y virtualbox-ose-guest-x11
modprobe vboxguest

echo ""
echo " * Launching MiG VNC proxy agent"
chmod +x /etc/init.d/migvncproxy
update-rc.d migvncproxy defaults
/etc/init.d/migvncproxy start
