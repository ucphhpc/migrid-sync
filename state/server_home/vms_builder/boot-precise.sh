#!/bin/bash
#
# Set up virtualbox guest additions and start MiG VNC proxy agent that relies
# on them for dynamic proxy settings

echo ""
echo " * Fixing repository"
echo "deb http://dk.archive.ubuntu.com/ubuntu/ precise main restricted universe" > /etc/apt/sources.list
echo "deb http://dk.archive.ubuntu.com/ubuntu/ precise-updates main restricted universe" >> /etc/apt/sources.list
echo "deb http://dk.archive.ubuntu.com/ubuntu/ precise-security main restricted universe" >> /etc/apt/sources.list
echo "deb http://security.ubuntu.com/ubuntu precise-security main restricted universe" >> /etc/apt/sources.list
# Try a few times to make sure we have a good chance even if network is
# lacking or still initializing
for i in 1 2 4 8 16 32; do
	apt-get update && break
	sleep $i
done

echo ""
echo " * Installing guest additions"
aptitude install -y linux-headers-generic-pae virtualbox-ose-guest-x11
modprobe vboxguest

echo ""
echo " * Launching MiG VNC proxy agent"
chmod +x /etc/init.d/migvncproxy
update-rc.d migvncproxy defaults
/etc/init.d/migvncproxy start
