<!-- 
Name: GCal
Author: Jonas Bardino <bardino AT nbi DOT ku DOT dk>
License: GPLv2
Description: Embedded google calender in iframe
Requires: jquery.js
-->
<script type="text/javascript">
    /* Configuration:
       Change next line to your google email address(es) and maybe edit time zone
    */
    var emails = ["YOUR_LOGIN@gmail.com"];
    var time_zone = 'Europe/Copenhagen';
    /* 
      Actual action - should not need user editing:
      Build embedded code with using HTTPS version of default proposed value
      from Google calendar -> Options -> Calendar details -> Embed ...
    */
    var url = 'https://www.google.com/calendar/embed?';
    for (index in emails) {
        url += 'src='+emails[index]+'&';
    }
    url += 'ctz='+time_zone;
    var layout = 'style="border: 0" width="800" height="300" frameborder="0"';
    layout += 'scrolling="no"';
    var embed_html = '<iframe src="'+url+'" '+layout+'></iframe>';
    $(document).ready(function() {
        $(".gcal").html(embed_html);
    });
</script>
<div class="gcal">
<p>Please enable Javascript to view this google calendar widget.</p>
</div>
