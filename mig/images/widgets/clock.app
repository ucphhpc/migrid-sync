<!-- 
Name: Clock
Author: Jonas Bardino <bardino AT diku DOT dk>
License: GPLv2
Description: Basic clock using JQuery epiclock plugin (modification of plugin demo)
Requires: jquery.js, jquery.epiclock.js, jquery.epiclock.css
-->
<script type="text/javascript">
$(document).ready(function() {
    $(".epiclock").html("");
    $(".epiclock").epiclock({format: 'r'});
    $.epiclock();
});
</script>
<div class="epiclock">
<p>Please enable Javascript to view this epiclock widget.</p>
</div>

