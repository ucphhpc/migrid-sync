<!--
Name: Certificate Countdown
Author: Ole B. Michelsen <ole AT michelsen DOT dk>
License: GPLv2
Description: Counts down to certificate expiry using JQuery countdown plugin
Requires: jquery.js, jquery.countdown.js, jquery.countdown.css
-->
<script type="text/javascript">
$(document).ready(function() {
    $.getJSON("userstats.py?output_format=json;stats=certificate", {}, function(jsonRes, textStatus) {
        var i = 0;
        var certificate = null;
        var today = new Date();
        // Grab results from json response and place them in resource status
        for(i=0; i<jsonRes.length; i++) {
            if (jsonRes[i].object_type == "user_stats") {
                certificate = jsonRes[i].certificate;
                var expire = new Date(certificate.expire);
                $("#cert_countdown").html("");
                $("#cert_countdown").countdown({until: expire});
                // Set warning date to 14 days prior to expire
                var days = 14;
                // Use date from time diff in ms to avoid calendar mangling
                var warning = new Date(expire.getTime() - days*24*60*60*1000);
                if(new Date().getTime() > warning.getTime()) {
                    $("#cert_countdown").addClass("red");
                }
                break;
            }
        }
    });
});
</script>
<style type="text/css">
    .hasCountdown { overflow: hidden; }
    .red { color: Red; }
</style>
<h4>Certificate expires in:</h4>
<div id="cert_countdown">No certificate data loaded.</div>
