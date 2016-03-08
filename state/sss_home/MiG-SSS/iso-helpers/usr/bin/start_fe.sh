#!/bin/bash
# Global vars
mig_user=mig
mig_home=/opt/mig

mig_tmp=${mig_home}/MiG

fe_home=${mig_home}/MiG/mig_frontend
fe_script=frontend_script.sh
fe_log=frontendlog

# Make /dev/null read/writeable	 
chmod 666 /dev/null

# Use local disk if available or fall back to writable tmpfs
# Parse kernel commandline options
for o in `cat /proc/cmdline` ; do
    case $o in 
    mig_disk=*)
        mig_disk=${o#mig_disk=}
        ;;
    esac
done
mig_disk="${mig_disk:-/dev/hda}"
echo "mounting $mig_disk"
mount ${mig_disk} /opt 2> /dev/null
if ! touch ${fe_home}/${fe_script} 2> /dev/null ; then
    echo "No writable MiG disk - using memory"
    mkdir -p /opt-rw
    mount -t tmpfs none /opt-rw
    rsync -a ${mig_home} /opt-rw/
    mount --bind /opt-rw/mig ${mig_home}
fi

# Make user mig owner of his home (linked to /opt/mig)
chown -R mig:mig /opt/mig 
       
# Protect /etc files from jobs (mig user)
chown -R root:root /opt/mig/etc
chmod -R 400 /opt/mig/etc

# Make sure FE dir is empty
if [ -e $fe_home ]; then
    rm -rf $fe_home
fi

# Create FE dir
mkdir -p ${fe_home}

# Set ownership of FE dir
chown -R ${mig_user}:${mig_user} ${fe_home}

sync

sandboxkey=`cat ${mig_home}/etc/keyfile`
migserver=`cat ${mig_home}/etc/serverfile`

# Get frontend script from MiG server
cmd="curl
       --fail 
       --silent                                                                                     
       --insecure
       --output ${mig_tmp}/${fe_script} 
       --url $migserver/cgi-sid/sandbox-getresourcescript.py?action=get_frontend_script&sandboxkey=$sandboxkey"

# Wait for frontend script to arrive
status=1
while [ $status -ne 0 ]; do
   #echo $cmd
   $cmd
   status=`head -n 1 ${mig_tmp}/${fe_script}`
   if [ $status -ne 0 ]; then
      sleep 5
   fi
done

# Remove status code from frontend script
cat ${mig_tmp}/${fe_script} | sed -e '1d' > ${fe_home}/${fe_script}
rm -f ${mig_tmp}/${fe_script}


# Change permissions on frontend script 
chmod 500 ${fe_home}/${fe_script}

sync

# Front end script must be run as root to protect sandboxkey from jobs
# Exe must be run as mig_user to protect system from jobs
# Fe and Exe need to write to shared job dirs
umask 0000

# Start frontend
cd ${fe_home}
./${fe_script}
