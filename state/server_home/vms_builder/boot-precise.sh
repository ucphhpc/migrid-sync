#!/bin/bash
echo ""
echo " * Fixing repository"
echo "deb http://ftp.klid.dk/ftp/ubuntu/ precise main restricted universe" > /etc/apt/sources.list
echo "deb http://ftp.klid.dk/ftp/ubuntu/ precise-updates main restricted universe" >> /etc/apt/sources.list
echo "deb http://ftp.klid.dk/ftp/ubuntu/ precise-security main restricted universe" >> /etc/apt/sources.list
echo "deb http://security.ubuntu.com/ubuntu precise-security main restricted universe" >> /etc/apt/sources.list
apt-get update
apt-get install -y linux-headers-`uname -r`

echo ""
echo " * Setting up auto-login"
sed -ie 's/^TimedLoginEnable=false/TimedLoginEnable=true/g' "/etc/gdm/gdm.conf"
sed -ie 's/^TimedLogin=/TimedLogin=mig/g' "/etc/gdm/gdm.conf"
sed -ie 's/^TimedLoginDelay=30/TimedLoginDelay=0/g' "/etc/gdm/gdm.conf"
sed -ie 's/^#KillInitClients=true/KillInitClients=false/g' "/etc/gdm/gdm.conf"

echo ""
echo " * Setting up autostart of x11vnc and proxyagent"

sed -ie 's/^exit 0//g' "/etc/gdm/Init/Default"

echo 'job_id=`VBoxControl -nologo guestproperty get job_id | cut -b 8-`' >> "/etc/gdm/Init/Default"
echo 'proxy_host=`VBoxControl -nologo guestproperty get proxy_host | cut -b 8-`' >> "/etc/gdm/Init/Default"
echo 'proxy_port=`VBoxControl -nologo guestproperty get proxy_port | cut -b 8-`' >> "/etc/gdm/Init/Default"
echo 'sed -ie "s/^identifier =.*/identifier = $job_id/g" "/opt/proxy/etc/proxyagent.conf"' >> "/etc/gdm/Init/Default"
echo 'sed -ie "s/^proxy_host =.*/proxy_host = $proxy_host/g" "/opt/proxy/etc/proxyagent.conf"' >> "/etc/gdm/Init/Default"
echo 'sed -ie "s/^proxy_port =.*/proxy_port = $proxy_port/g" "/opt/proxy/etc/proxyagent.conf"' >> "/etc/gdm/Init/Default"
echo 'echo $job_id >> /tmp/test_par' >> "/etc/gdm/Init/Default"
echo 'echo $proxy_host >> /tmp/test_par' >> "/etc/gdm/Init/Default"
echo 'echo $proxy_port >> /tmp/test_par' >> "/etc/gdm/Init/Default"

echo "cd /opt/proxy/" >> "/etc/gdm/Init/Default"
echo "/usr/bin/python proxyagent.py" >> "/etc/gdm/Init/Default"
echo "/usr/bin/x11vnc -rfbport 5900 -shared -forever -bg -noxdamage" >> "/etc/gdm/Init/Default"
echo "exit 0" >> "/etc/gdm/Init/Default"

echo ""
echo " * Installing guest additions"

ARCH=`uname -m`
if [ "$ARCH" == "x86_64" ]; then
  `chmod +x /opt/VBoxLinuxAdditions-amd64.run`
  `/opt/VBoxLinuxAdditions-amd64.run`
else
  `chmod +x /opt/VBoxLinuxAdditions-x86.run`
  `/opt/VBoxLinuxAdditions-x86.run`
fi 
