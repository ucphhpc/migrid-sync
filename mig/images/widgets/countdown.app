<!-- 
Name: Countdown
Author: Jonas Bardino <bardino AT diku DOT dk>
License: GPLv2
Description: Basic count down using JQuery countdown plugin (modification of plugin demo)
Requires: jquery.js, jquery.countdown.js, jquery.countdown.css
-->
<script type="text/javascript">
$(document).ready(function() {
    var today = new Date();
    var future = new Date(today.getFullYear() + 1, 0, 0);
    $(".countdown").html("");
    $(".countdown").countdown({until: future});
});
</script>
<h3>Time to new year</h3>
<div class="countdown">
<p>Please enable Javascript to view this countdown widget.</p>
</div>

