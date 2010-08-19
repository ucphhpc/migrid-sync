<!--
Name: Jobs Stats
Author: Ole B. Michelsen <ole AT michelsen DOT dk>
License: GPLv2
Description: Table of job states for all jobs
Requires: jquery.js
-->
<script type="text/javascript">
$(document).ready(function() {
    $.getJSON("userstats.py?output_format=json;stats=jobs", {}, function(jsonRes, textStatus) {
                var i = 0;
                var jobs = null;
                var htmlOut = null;
                // Grab results from json response and place them in job status
                for(i=0; i<jsonRes.length; i++) {
                        if (jsonRes[i].object_type == "user_stats") {
                                jobs = jsonRes[i].jobs;
                                htmlOut = "<table>" +
                                        "<tr><th>Total:</th><td>" + jobs.total + "</td></tr>" +
                                        "<tr><th>Parse:</th><td>" + jobs.parse + "</td></tr>" +
                                        "<tr><th>Queued:</th><td>" + jobs.queued + "</td></tr>" +
                                        "<tr><th>Executing:</th><td>" + jobs.executing + "</td></tr>" +
                                        "<tr><th>Finished:</th><td>" + jobs.finished + "</td></tr>" +
                                        "<tr><th>Retry:</th><td>" + jobs.retry + "</td></tr>" +
                                        "<tr><th>Cancelled:</th><td>" + jobs.canceled + "</td></tr>" +
                                        "<tr><th>Expired:</th><td>" + jobs.expired + "</td></tr>" +
                                        "<tr><th>Failed:</th><td>" + jobs.failed + "</td></tr>" +
                                        "</table>";
                                $("#jobs_stats_tbl").html("");
                                $("#jobs_stats_tbl").append(htmlOut);
                                break;
                        }
                }
        });
});
</script>
<h4>Jobs</h4>
<div id="jobs_stats_tbl">No jobs data loaded.</div>
