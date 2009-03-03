#!/bin/sh
function add_permissions(){
	 migserver="$1"
	 migport="$2"
	 keyfile="$3"
	 cp -f $POLICY_TEMPLATE_FILE $POLICY_FILE
	 
	 # Grant permissions to local JvmExecuter,' 	                  		    
	 # Note that executing jobs, will _NOT_ get theese permissions.'       		    
	 
	 # These Permissions only granted to specific jarfile
	 echo 'grant codeBase "file:'$PWD'/'$JAR_FILE'" {'                           		     >> $POLICY_FILE
	 
	 # Grant permission to read and write keyfile
	 echo 'permission java.io.FilePermission "'$PWD/$keyfile'","read,write";'    		     >> $POLICY_FILE
	 
	 # Grant permission to overrule SSLSocket factory, needed for connection to untrusted SSL resource ( The MiG-Server )
      	 echo 'permission java.lang.RuntimePermission "setFactory";'                 		     >> $POLICY_FILE
	 
	 # Grant permission to connect,accept and resolve the MiG-server we shall connect to.
     	 echo 'permission java.net.SocketPermission "'$migserver'", "connect,accept,resolve";'	     >> $POLICY_FILE
      	 echo 'permission java.net.SocketPermission "'$migserver:$migport'", "connect,resolve";'     >> $POLICY_FILE
	 
	 # Grant permission to create classloader
	 echo 'permission java.lang.RuntimePermission "createClassLoader";'       	             >> $POLICY_FILE
	 	 
      	 #echo 'permission java.security.AllPermission;' 		    	 		     >> $POLICY_FILE
	 echo '};'                                                                   		     >> $POLICY_FILE
	 
	 # These Permissions are granted to alle files from the MiG server
	 echo 'grant codeBase "url:https://'$migserver':'$migport'/-" {'                       	     >> $POLICY_FILE
	 
	 # Grant permission to connect,accept and resolve the MiG-server we shall connect to.
     	 echo 'permission java.net.SocketPermission "'$migserver'", "connect,accept,resolve";'	     >> $POLICY_FILE
      	 echo 'permission java.net.SocketPermission "'$migserver:$migport'", "connect,resolve";' >> $POLICY_FILE
	 
	 # Grant permission to create classloader
	 #echo 'permission java.lang.RuntimePermission "createClassLoader";'       	             >> $POLICY_FILE
	 echo '};'                                                                   		     >> $POLICY_FILE
}

function start_resource_jvm(){
        migserver="$1"
	migport="$2"
	keyfile="$3"
	oneshot="$4"
       	add_permissions $migserver $migport $keyfile
	cmd="nice -19 java -Xmx128m -cp $JAR_FILE -Djava.security.manager -Djava.security.policy=$POLICY_FILE $EXE_FILE $migserver:$migport $keyfile $oneshot"
	echo $cmd
	$cmd
}	
      
function usage(){
        echo "Usage..."
	echo "$0"
	echo "Example: $0"
}


########
# Main #
########
MiGOneClickConsoleconf=./MiGOneClickConsole.conf

if [ ! -r $MiGOneClickConsoleconf ]; then
   echo "$0 requires a readable configuration in $MiGOneClickConsoleconf"
   usage  
   exit 1
fi


keyfile="`hostname`.`domainname`.key"
POLICY_FILE="$keyfile.policy"
POLICY_TEMPLATE_FILE="MiGOneClick.policy.template"
JAR_FILE=MiGOneClickConsole.jar
EXE_FILE=MiGOneClickConsole

migserver=`awk '/migserver/ {print $2}' $MiGOneClickConsoleconf`
migport=`awk '/migport/ {print $2}' $MiGOneClickConsoleconf`
oneshot=`awk '/oneshot/ {print $2}' $MiGOneClickConsoleconf`

if [ $# -eq 0 ]; then
	start_resource_jvm $migserver $migport $keyfile $oneshot
else
	usage
	exit 1
fi
      
