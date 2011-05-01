<!-- 
Name: RSS Feed Reader
Author: Jonas Bardino <bardino AT diku DOT dk>
License: GPLv2
Description: Pulls in MiG changelog with JQuery zrssfeed plugin (modification of plugin demo)
Requires: jquery.js, jquery.zrssfeed.js, jquery.zrssfeed.css
-->
<script type="text/javascript">
$(document).ready(function() {
    $(".rssfeed").html("");
    $(".rssfeed").rssfeed('https://code.google.com/feeds/p/migrid/svnchanges/basic', {
    limit: 3,
    ssl: true
  });
});
</script>
<div class="rssfeed">
<p>Please enable Javascript to view this rssfeed widget.</p>
</div>

