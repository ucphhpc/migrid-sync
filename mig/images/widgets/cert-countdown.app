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
        // Set color warning these many days prior to expire
        var low_days = 28;
        var mid_days = 14;
        var high_days = 7;
        var day_msecs = 24*60*60*1000;
        var today = new Date();
        // Grab results from json response and place them in resource status
        for(i=0; i<jsonRes.length; i++) {
            if (jsonRes[i].object_type == "user_stats") {
                certificate = jsonRes[i].certificate;
                var expire = new Date(certificate.expire);
                $("#cert_countdown").html("");
                $("#cert_countdown").countdown({until: expire});
                // Use date from time diff in ms to avoid calendar mangling
                var high_warn = new Date(expire.getTime() - high_days*day_msecs);
                var mid_warn = new Date(expire.getTime() - mid_days*day_msecs);
                var low_warn = new Date(expire.getTime() - low_days*day_msecs);
                if(new Date().getTime() > high_warn.getTime()) {
                    $("#cert_countdown").addClass("highwarn");
                } else if(new Date().getTime() > mid_warn.getTime()) {
                    $("#cert_countdown").addClass("midwarn");
                } else if(new Date().getTime() > low_warn.getTime()) {
                    $("#cert_countdown").addClass("lowwarn");
                }
                break;
            }
        }
    });
});
</script>
<style type="text/css">
    .hasCountdown { overflow: hidden; }
    .highwarn { color: red; }
    .midwarn { color: orange; }
    .lowwarn { color: yellow; }
</style>
<h4>Certificate expires in:</h4>
<div id="cert_countdown">No certificate data loaded.</div>
