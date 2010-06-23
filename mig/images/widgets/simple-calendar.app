<!-- 
Name: Simple calendar
Requires: jquery.js, jquery.calendar-widget.js
-->
<script type="text/javascript">
$(document).ready(function() {
    var today = new Date();
    $(".simplecalendar").calendarWidget({
    month: today.getMonth(),
    year: today.getFullYear()
    });
});
</script>
<div class="simplecalendar">
<p>Please enable Javascript to view this calendar widget.</p>
</div>

