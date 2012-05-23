#!/bin/bash
#
# Generates html index of qcow2 and vmdk images in target dir 
#
# Please refer to usage help for details

# Change run to 'echo' to only show commands for partial manual runs
#run='echo'
run=''

usage() {
    echo "USAGE: $0 SOURCEDIR
Generates a html index of qcow2 and vmdk image files in SOURCEDIR.

Typically called with something like
$0 ~/state/wwwpublic/vm-packs/vbox3.1-os-images-2012-1
to generate the html index for the image files in a vm-packs subdir.
"
}

if [ $# -lt 1 ]; then
    usage
    exit 1
fi

srcdir="$1"
if [ ! -d $srcdir ]; then
    echo "No such input dir: $srcdir"
    usage
    exit 1
fi
index="$srcdir/index.html"

$run sync
echo '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
<title>MiG Virtual Machine Images</title>
<meta http-equiv="content-type" content="text/html; charset=UTF-8">
<meta name="generator" content="emacs">
<meta name="description" content="MiG virtual machine images">
<meta name="keywords" content="virtual machine image">
<meta name="copyright" content="The MiG team lead by Brian Vinter">
<link rel="stylesheet" type="text/css" href="/images/site.css" media="screen"/>
<link rel="stylesheet" type="text/css"
      href="/images/css/jquery.managers.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/jquery-ui.css"
      media="screen"/>
</head>
<body>
<div class="title">
<h1>MiG Virtual Machine Images</h1>
</div>
<div id="content">
<h1>Individual Images</h1>' > $index
echo '<ul>' >> $index

for src in $(ls $srcdir/*.vmdk $srcdir/*.qcow2 2> /dev/null); do
    echo "Adding $src"
    img=$(basename $src)
    echo '<li><a href="'$img'">'$img'</a></li>' >> $index
done
echo '</ul>' >> $index
echo '</div>
</body>
</html>' >> $index

$run sync
