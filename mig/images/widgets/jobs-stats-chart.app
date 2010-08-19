<!--
Name: Job Stats Chart
Author: Ole B. Michelsen <ole AT michelsen DOT dk>
License: GPLv2
Description: Pie chart with job states using jQuery Google Charts plugin
Requires: jquery.js, jquery.jgcharts.js
-->
<script type="text/javascript">
$(document).ready(function() {
        function updateChart() {
                $.getJSON("userstats.py?output_format=json;stats=jobs", {}, function(jsonRes, textStatus) {
                        var i = 0;
                        var jobs = null;
                        // Grab results from json response and place them in chart
                        for(i=0; i<jsonRes.length; i++) {
                                if (jsonRes[i].object_type == "user_stats") {
                                        jobs = jsonRes[i].jobs;
                                        $("#jobs_stats_chart div").html("");
                                        $("#jobs_stats_chart div").append(jobs.total + " jobs total");
                                        var api = new jGCharts.Api();
                                        $("#jobs_stats_chart img").attr('src', api.make(
                                                {
                                                        type: 'p',
                                                        size: '400x200',
                                                        data: [jobs.parse, jobs.queued, jobs.executing, jobs.finished, jobs.retry, jobs.canceled, jobs.expired, jobs.failed],
                                                        axis_labels : ['Parse', 'Queued', 'Executing', 'Finished', 'Retry', 'Cancelled', 'Expired', 'Failed']
                                                }
                                        ));
                                        break;
                                }
                        }
                });
                setTimeout(updateChart, 60000);
    }
    updateChart();
});
</script>
<div id="jobs_stats_chart">
    <!-- dynamic update by jquery -->
    <img src='' alt="PieChart" />
    <div>No jobs data loaded.</div>
</div>
