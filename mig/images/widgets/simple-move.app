<!-- 
Name: Simple move
Author: Jonas Bardino <bardino AT diku DOT dk>
License: GPLv2
Description: Movable widgets using the JQuery UI Sortable widget (modification of default demo)
Requires: jquery.js, jquery-ui.js, jquery-ui.css
-->
<style type="text/css">
#movearea { width: 100%; float: right; }
#sortablelist { list-style-type: none; margin: 0; padding: 0; }
#sortablelist li { float: left; margin: 0 0px 1px 1px; padding: 0.4em; padding-left: 1.5em; }
#sortablelist li span { position: absolute; margin-left: -1.3em; }
</style>
<script type="text/javascript">
$(function() {
	     $("#sortablelist").sortable();
	     $("#sortablelist").disableSelection();
});
</script>
<div id="movearea">
<ul id="sortablelist">
    <li class="ui-state-default"><span class="ui-icon ui-icon-arrowthick-2-e-w"></span>1</li>
    <li class="ui-state-default"><span class="ui-icon ui-icon-arrowthick-2-e-w"></span>2</li>
    <li class="ui-state-default"><span class="ui-icon ui-icon-arrowthick-2-e-w"></span>3</li>
    <li class="ui-state-default"><span class="ui-icon ui-icon-arrowthick-2-e-w"></span>4</li>
</ul>
</div>
<div id="movetext">
<p>
Drag the number boxes above around as you like to swap their positions.
</p>
</div>
