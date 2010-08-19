<!-- 
Name: Job Monitor
Author: Jonas Bardino <bardino AT diku DOT dk>
License: GPLv2
Description: Basic job monitor showing latest five jobs
Requires: jquery.js
-->
<script type="text/javascript">
function latestJobsPattern() {
    var now = new Date();
    return '*_'+now.getFullYear()+'_*';
}
function refreshJobs(jobs, max_jobs) {
    $("#jobmonitor tbody tr").html("<td colspan=3>Loading ...</td>");
    $.getJSON("jobstatus.py", {job_id: jobs, output_format: 'json',
    	  'flags': 's', max_jobs: max_jobs},
    function(jsonRes, textStatus) {
        var jobList = new Array();
        for(var i = 0; i < jsonRes.length; i++) {
            if ((jsonRes[i].object_type == "job_list") &&
    		    (jsonRes[i].jobs.length > 0)) {
                jobList = jobList.concat(jsonRes[i].jobs);
            } else if (jsonRes[i].object_type=='error_text') {
                var error = jsonRes[i].text;
                alert('load job status error:' + error);
            }
        }
        $("#jobmonitor tbody").html("");
        // Wrap each json result into html
        $.each(jobList, function(i, item) {
            $("#jobmonitor tbody").append("<tr>"+"<td>"+item.job_id+"</td>"+
              "<td><div class='jobstatus'>"+item.status+"</div></td>"+
              "<td>"+item.received_timestamp+"</td>"+"</tr>"
              );
        });
    });
}
$(document).ready(function() {
    refreshJobs(latestJobsPattern(), 5);
    setInterval("refreshJobs('" + latestJobsPattern() + "', 5)", 120000);
});
</script>
<div id="jobstatusmonitor">
<!-- dynamic update by jquery -->
      <table id="jobmonitor">
      <thead>
        <tr>
          <th>Job ID</th>
          <th style="width: 150px;">Status</th>
          <th style="width: 250px;">Date</th>
        </tr>
      </thead>
      <tbody>
        <tr><td colspan=3>Please enable Javascript to view this job monitor widget.</td></tr>
      </tbody>
    </table>
</div>
