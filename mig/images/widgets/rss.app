<!-- 
Name: RSS Feed Reader
Requires: jquery.js, jquery.zrssfeed.js, jquery.zrssfeed.css
-->
<script type="text/javascript">
$(document).ready(function() {
    $(".rssfeed").html("");
    $(".rssfeed").rssfeed('https://code.google.com/feeds/p/migrid/svnchanges/basic', {
    limit: 3
  });
});
</script>
<div class="rssfeed">
<p>Please enable Javascript to view this rssfeed widget.</p>
</div>

