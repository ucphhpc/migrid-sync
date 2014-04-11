<!--
Name: Certificate Countdown
Author: Ole B. Michelsen <ole AT michelsen DOT dk>
License: GPLv2
Description: Counts down to certificate expiry using JQuery countdown plugin
Requires: jquery.js, jquery.countdown.js, jquery.countdown.css
-->
<script type="text/javascript">
$(document).ready(function() {
    // Append custom css to head tag since inline style is not strictly valid
    var extra_style = '<style type="text/css">\n';
    // remove padding to avoid seconds entry below rest in Chrome
    extra_style += '  .countdown_row { padding: 0; }\n';
    extra_style += '  .hasCountdown { overflow: hidden; }\n';
    extra_style += '  .highwarn { color: red; }\n';
    extra_style += '  .midwarn { color: orange; }\n';
    extra_style += '  .lowwarn { color: yellow; }\n';
    extra_style += '</style>\n';
    $('head').append(extra_style);
    $.getJSON("userstats.py?output_format=json;stats=certificate", {}, function(jsonRes, textStatus) {
        var i = 0;
        var certificate = null;
        // Set color warning these many days prior to expire
        var low_days = 28;
        var mid_days = 14;
        var high_days = 7;
        var day_msecs = 24*60*60*1000;
        var today = new Date();
        var expire = new Date(today.getTime());
        // Grab results from json response and place them in resource status
        for(i=0; i<jsonRes.length; i++) {
            if (jsonRes[i].object_type == "user_stats") {
                certificate = jsonRes[i].certificate;
                // server returns -1 if no cert info is available
                if (certificate.expire != -1) {
                    expire = new Date(certificate.expire);
                }
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
<h4>Certificate expires in:</h4>
<div id="cert_countdown" class="smallcontent">No certificate data loaded.</div>
