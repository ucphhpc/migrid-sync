<!-- 
Name: Progress Bar
Author: Jonas Bardino <bardino AT nbi DOT ku DOT dk>
License: GPLv2
Description: Dummy progress bas using JQuery UI progressbar widget (modification of default demo)
Requires: jquery.js, jquery-ui.js, jquery-ui.css, jquery-ui-theme.css
-->
<script type="text/javascript">
$(document).ready(function() {
    function onProgress() {
        $(".progresslabel").text($(".progressbar").progressbar("option", "value") + "%");
    }
    function startProgress() {
        var count = $(".progressbar").progressbar("option", "value") +	1;
        $(".progressbar").progressbar("option", "value", count);
        if(count < 100) {
            setTimeout(startProgress, 1000);
        }
    }
    $(".progressbar").html("");
    $(".progressbar").progressbar({change: onProgress});
    startProgress();
});
</script>
<div class="progressbar">
<p>Please enable Javascript to view this progressbar widget.</p>
</div>
<div class="progresslabel">
0%
</div>
