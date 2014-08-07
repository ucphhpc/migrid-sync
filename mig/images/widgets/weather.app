<!-- 
Name: Weather
Author: Jonas Bardino <bardino AT nbi DOT ku DOT dk>
License: GPLv2
Description: Copenhagen weather using JQuery zweatherfeed plugin (modification of plugin demo)
Requires: jquery.js, jquery.zweatherfeed.js, jquery.zweatherfeed.css
-->
<script type="text/javascript">
$(document).ready(function() {
    $(".weatherfeed").html("");
    $(".weatherfeed").weatherfeed(['DAXX0009']);
});
</script>
<div class="weatherfeed">
<p>Please enable Javascript to view this weatherfeed widget.</p>
</div>
