#!/bin/bash
#
# Show basic stats about migrid users and storage use
# Optionally limits df output to any file system types given on command-line

# NOTE: We expect script to be in ~/mig/server/ and state in ~/state but we
#       dynamically deduct the root to only really rely on the sub-structure.
SCRIPTPATH=$(realpath $0)
SERVERDIR=$(dirname $SCRIPTPATH)
MIGDIR=$(dirname $SERVERDIR)
BASEDIR=$(dirname $MIGDIR)
STATEDIR="$BASEDIR/state"
# For absolute mig.X imports
export PYTHONPATH="$BASEDIR"

declare -a DFOPTS
for FSTYPE in $@; do
    FSOPTS+=("-t $FSTYPE")
done

echo "=== Disk Use ==="
df -h ${FSOPTS[@]}

echo "=== Disk Mounts ==="
mount ${FSOPTS[@]}

echo "Where"
echo " * vgrid_files_home is all vgrid shared folders"
echo " * vgrid_private_base/vgrid_public_base are all vgrid web portals"
echo " * user_home is all user home dirs"
echo " * freeze_home is frozen archives from all users"

echo ""

echo "== Totals =="
echo "=== Registered Local Users ==="
$SERVERDIR/searchusers.py -f distinguished_name | grep -v 'Matching users' | sort | uniq | wc -l

echo "=== Registered VGrids ==="
# NOTE: no maxdepth since nested vgrids are allowed, mindepth is known for target, however
find $STATEDIR/vgrid_home -mindepth 1 -type d | grep -v '/\.' | wc -l

echo "=== Frozen Archives ==="
# TODO: update to fit only new client_id location when migrated
find $STATEDIR/freeze_home -mindepth 2 -maxdepth 3 -type f -name meta.pck | wc -l

echo ""

echo "== This Week =="
echo "=== Registered and Renewed Local Users ==="
# NOTE: first or repeat signup sets expire field to 365 days into the future.
# We simply lookup all users with expire more than 358 days from now.
RECENT=$(date +'%s')
RECENT=$((RECENT+(365-7)*24*3600))
$SERVERDIR/searchusers.py -f distinguished_name -a $RECENT | grep -v 'Matching users' | sort | uniq | wc -l

echo "=== Registered and Updated VGrids ==="
# NOTE: no maxdepth since nested vgrids are allowed, mindepth is known for target, however
# NOTE: vgrid_home/X ctime also gets updated on any file changes in that dir
find $STATEDIR/vgrid_home -mindepth 1 -type d -ctime -7 | grep -v '/\.' | wc -l

echo "=== Frozen Archives ==="
# NOTE: meta.pck file never changes for archives
# TODO: update to fit only new client_id location when migrated
find $STATEDIR/freeze_home -mindepth 2 -maxdepth 3 -type f -name meta.pck -ctime -7 | wc -l

echo ""

echo "== User Distribution =="
echo "=== By Organisation ==="
$SERVERDIR/searchusers.py -f distinguished_name | grep -v 'Matching users' | python $SERVERDIR/countorg.py

echo "=== By Email Domain ==="
$SERVERDIR/searchusers.py -f email | grep -v 'Matching users' | python $SERVERDIR/countemail.py
