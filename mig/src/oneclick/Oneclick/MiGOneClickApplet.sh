#!/bin/sh
#
# MiGOneClickApplet - One-Click applet wrapper for execution outside a browser
# Copyright (C) 2007  Martin Rehr
# 
# This file is part of MiG.
# 
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# MiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


function add_permissions(){
	 migserver="$1"
	 migport="$2"
	 cp -f $POLICY_TEMPLATE_FILE $POLICY_FILE
	 
	 # These Permissions are granted to alle files from the MiG server
	 echo 'grant codeBase "url:https://'$migserver':'$migport'/-" {'                       	     >> $POLICY_FILE
	 
	 # Grant permission to connect,accept and resolve the MiG-server we shall connect to.
     	 echo 'permission java.net.SocketPermission "'$migserver'", "connect,accept,resolve";'	     >> $POLICY_FILE
      	 echo 'permission java.net.SocketPermission "'$migserver:$migport'", "connect,resolve";'     >> $POLICY_FILE
	 
	 # Grant permission to create classloader
	 echo 'permission java.lang.RuntimePermission "createClassLoader";'       	             >> $POLICY_FILE
	 echo '};'                                                                   		     >> $POLICY_FILE
}

MiGOneClickConsoleconf=./MiGOneClickConsole.conf
if [ ! -r $MiGOneClickConsoleconf ]; then
   echo "$0 requires a readable configuration in $MiGOneClickConsoleconf"
   exit 1
fi

migserver=`awk '/migserver/ {print $2}' $MiGOneClickConsoleconf`
migport=`awk '/migport/ {print $2}' $MiGOneClickConsoleconf`


POLICY_FILE="`hostname`.`domainname`.appletviewer.policy"
POLICY_TEMPLATE_FILE="MiGOneClick.policy.template"

add_permissions $migserver $migport
URL="https://$migserver:$migport/cgi-sid/oneclick"
cmd="appletviewer -J-Djavax.net.ssl.trustStore=SSLStore -J-Djavax.net.ssl.trustStorePassword=tl1000r -J-Djava.security.manager -J-Djava.security.policy=$POLICY_FILE $URL"
echo $cmd
$cmd
