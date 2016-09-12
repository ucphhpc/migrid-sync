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
# TODO: update to fit only new clien_id location when migrated
find $STATEDIR/freeze_home -maxdepth 2 -type d -name 'archive-*' | wc -l

echo ""

echo "== This Week =="
echo "=== Registered Users ==="
# NOTE: we explicitly seach in +C=* to avoid symlink redundancy
# .htaccess generally remains unchanged except if user signs up again.
# TODO: this is inaccurate as user_home ctime gets updated (by gluster?)
# TODO: add ctime option to searchusers script and use that instead?
#find $STATEDIR/user_home -maxdepth 1 -type d -ctime -7 | grep -v .svn | wc -l
find $STATEDIR/user_home/+C=* -maxdepth 1 -type f -name '.htaccess' -ctime -7 | wc -l

echo "=== Registered VGrids ==="
# NOTE: no maxdepth since nested vgrids are allowed, mindepth is known for target, however
# TODO: this is inaccurate as vgrid_home ctime gets updated (by gluster or dircache?)
#find $STATEDIR/vgrid_home -type d -ctime -7 | grep -v .svn | wc -l
#find $STATEDIR/vgrid_public_base -type f -path '.vgridscm/cgi-bin/hgweb.cgi' -ctime -7 | wc -l
find $STATEDIR/vgrid_public_base -mindepth 3 -type f -path '*/.vgridscm/cgi-bin/hgweb.cgi' -ctime -7 | wc -l

echo "=== Frozen Archives ==="
# TODO: update to fit only new client_id location when migrated
find $STATEDIR/freeze_home -mindepth 2 -maxdepth 3 -type f -name meta.pck -ctime -7 | wc -l
