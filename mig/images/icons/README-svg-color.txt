SVG files are plain XML and contain a simple fill value with the html color
code. The originals were prepared for ERDA UCPH Science skin colors (#46743c)
but custom skin colors for e.g. our X-basic skins can easily be generated with
something like:
for i in *.svg; do grep -q -i 46743c $i && cp $i ${i/.svg/_46743c.svg}; cat $i | sed 's/46743c/147/ig' > ${i/.svg/_114477.svg}; done
