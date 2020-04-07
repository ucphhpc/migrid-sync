SVG files are plain XML and contain a simple fill value with the html color
code. The originals were prepared for ERDA UCPH Science skin colors (#46743c)
but custom skin colors for e.g. our X-basic skins can easily be generated with
something like:
for i in *.svg; do grep -q -i 46743c $i && cp $i ${i/.svg/_46743c.svg}; cat $i | sed 's/46743c/147/ig' > ${i/.svg/_114477.svg}; done

For additional SVG icons and logos we can use whatever we can find online, as
long as they come with an easy to follow license.
SVG Repo (https://www.svgrepo.com/) and similar pages have a bunch of Creative
Commons CC0 / Public Domain SVGs that can be used without attribution on every
single page where they are used. So we can just stick a note in the License and
Credits on the docs page as usual.
When using SVGs from there we typically need to open the file in an editor and
add class="st0" to all svg elements we want to style and then insert a simple
style rule for that class at the top right after the svg element like:
style type="text/css">
          .st0{fill:#147;}                                                                               
</style>

Please have a look e.g. at images/icons/lightbulb_idea.svg for an extensive
example. 
