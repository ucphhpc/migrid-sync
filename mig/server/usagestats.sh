#!/bin/bash
#
# Show basic stats about migrid users and storage use
# Optionally limits df output to any file system types given on command-line

SERVERDIR=$(dirname $0)
if [ -z "$SERVERDIR" ]; then
    SERVERDIR="."
fi
STATEDIR="$SERVERDIR/../../state"

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
echo "=== Registered Users ==="
$SERVERDIR/searchusers.py | grep -v 'Matching users' | sed 's/ : .*//g' | sort | uniq | wc -l

echo "=== Registered VGrids ==="
find $STATEDIR/vgrid_home -type d | grep -v .svn | wc -l

echo "=== Frozen Archives ==="
find $STATEDIR/freeze_home -maxdepth 1 -type d -name 'archive-*' | wc -l

echo ""

echo "== This Week =="
echo "=== Registered Users ==="
find $STATEDIR/user_home -maxdepth 1 -type d -ctime -7 | grep -v .svn | wc -l

echo "=== Registered VGrids ==="
find $STATEDIR/vgrid_home -maxdepth 1 -type d -ctime -7 | grep -v .svn | wc -l

echo "=== Frozen Archives ==="
find $STATEDIR/freeze_home -maxdepth 1 -type d -name 'archive-*' -ctime -7 | wc -l
