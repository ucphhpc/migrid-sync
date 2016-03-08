#!/bin/bash
# Global vars
mig_user=mig
mig_home=/opt/mig

mig_tmp=${mig_home}/MiG

exe_home=${mig_home}/MiG/mig_exe
exe_script=master_node_script.sh

forkwait=/usr/bin/forkwait
master_pgidfile=/var/run/MiG_master.pgid

sandboxkey=`cat ${mig_home}/etc/keyfile`
migserver=`cat ${mig_home}/etc/serverfile`

# Make sure EXE dir is empty
if [ -e $exe_home ]; then
    rm -rf $exe_home
fi

# Create EXE dir
mkdir -p ${exe_home}

# Set ownership of EXE dir
chown -R ${mig_user}:${mig_user} ${exe_home}

# Get master node script from MiG server
cmd="curl
       --fail 
       --silent                                                                                                         
       --insecure
       --output ${mig_tmp}/${exe_script} 
       --url $migserver/cgi-sid/sandbox-getresourcescript.py?action=get_master_node_script&sandboxkey=$sandboxkey"

# Wait for master node script to arrive
status=1
while [ $status -ne 0 ]; do
   #echo $cmd
   $cmd
   status=`head -n 1 ${mig_tmp}/${exe_script}`
   if [ $status -ne 0 ]; then
      sleep 5
   fi
done

# Remove status code from master node script
cat ${mig_tmp}/${exe_script} | sed -e '1d' > ${exe_home}/${exe_script}
rm -f ${mig_tmp}/${exe_script}

# Change permissions and owner ship on master node script
chmod 500 ${exe_home}/${exe_script}
chown -R ${mig_user}:${mig_user} ${exe_home}/${exe_script}

# Start master node script as mig user
cd ${exe_home}
while [ /bin/true ]; do
   ${forkwait} "cd ${exe_home} && su mig ./${exe_script}" "${master_pgidfile}"
done &

echo "#################################################################"
echo "#################################################################"
echo "#################################################################"
echo "#######   ###########   ####################           ##########"
echo "#######    #########    ###################  #########  #########"
echo "#######  #  #######  #  ##################  ###########  ########"
echo "#######  ##  #####  ##  #################  #############  #######"
echo "#######  ###  ###  ###  #################  ######################"
echo "#######  ####  #  ####  ########  #######  ######################"
echo "#######  #####   #####  ########  #######  ######################"
echo "#######  #############  #################  ######################"
echo "#######  #############  #################  ######################"
echo "#######  #############  ########  #######  #####          #######"
echo "#######  #############  ########  #######  #####  ######  #######"
echo "#######  #############  ########  #######  #####  ######  #######"
echo "#######  #############  ########  #######  #############  #######"
echo "#######  #############  ########  ########  ###########  ########"
echo "#######  #############  ########  #########  #########  #########"
echo "#######  #############  ########  ##########           ##########"
echo "#################################################################"
echo "#################################################################"
echo "######### Effectively putting your idle resources to use ########"
echo "#################################################################"
echo "#################################################################"
echo "#################################################################"
