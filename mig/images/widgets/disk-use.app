<!--
Name: Disk Use Progress Bar
Author: Ole B. Michelsen <ole AT michelsen DOT dk>
License: GPLv2
Description: Progress bar of used disk space in MiG, assumes a quota of 1 GB
Requires: jquery.js, jquery-ui.js, jquery-ui.css
-->
<script type="text/javascript">
$(document).ready(function() {
        function roundNumber(num, dec) {
                return Math.round(num*Math.pow(10,dec))/Math.pow(10,dec);
        }
        $.getJSON("userstats.py?output_format=json;stats=disk", {}, function(jsonRes, textStatus) {
                var i = 0;
                var disk = null;
                var quota = 1024; // Setting the disk quota
                // Grab results from json response and place them in resource status.
                for(i=0; i<jsonRes.length; i++) {
                        if (jsonRes[i].object_type == "user_stats") {
                                disk = jsonRes[i].disk;
                                var mb = roundNumber(disk.own_megabytes, 2);
                                var percent = (mb > 0) ? Math.round(mb / quota * 100) : 0;
                                var htmlLabel = mb + " MB of " + quota + " MB";
                                $("#disk_use_progressbar").html("");
                                $("#disk_use_progressbar").progressbar({ value: percent});
                                $("#disk_use_progresslabel").text(htmlLabel);
                                break;
                        }
                }
        });
});
</script>
<h4>Disk use:</h4>
<div id="disk_use_progressbar">Please enable JavaScript</div>
<div id="disk_use_progresslabel">0 MB</div>
