#!/bin/sh
#
# Clean up resource after job execution

CLEAN_LOG="MiG/clean.log"

log() {
	[ -e "$CLEAN_LOG" ] || touch $CLEAN_LOG
	echo "$(date "+%d/%m-%Y %H:%M:%S") : $@" >> $CLEAN_LOG
}

delete() {
	path="$1"
	log "cleaning $path"
	rm -rf $path
}

subkill() {
	PGID="$1"
	for pid in `ps -o pid= -g $PGID`; do
		if [ $PGID -ne $pid ]; then
			log "kill child process $pid: $(ps $pid)"
			kill -9 $pid
		fi
	done
}

FE="NOSUCHHOST"
NODE="NOSUCHHOST"
PGID=99999
if [ $# -gt 0 ]; then
	FE="$1"
fi
if [ $# -gt 1 ]; then
	NODE="$2"
fi
if [ $# -gt 2 ]; then
	PGID="$3"
fi

EXE_DIR="MiG/mig_exe/$FE/$NODE"

# Delete leftover job dirs and files in exe dir
for path in $EXE_DIR/job-dir_*; do
	# Ignore case where no matching files were found
	if [ "$EXE_DIR/job-dir_*" != "$path" ]; then 
		delete "$path"
	fi
done
for path in $EXE_DIR/[0123][0-9]*; do
	# Ignore case where no matching files were found
	if [ "$EXE_DIR/[0123][0-9]*" != "$path" ]; then 
		delete "$path"
	fi
done

echo $PGID | grep -E '^[0-9]+$' > /dev/null
if [ $? -ne 0 ]; then
	log "Not a real PGID \"$PGID\" - not killing any processes"
	exit 0
fi

# Kill all non MiG processes in PGID
log "kill subprocesses of $PGID"
subkill $PGID
