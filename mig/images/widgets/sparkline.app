<!--
Name: Sparkline
Author: Jonas Bardino <bardino AT diku DOT dk>
License: GPLv2
Description: Inline mini chart using JQuery Sparklines plugin (modification of default demo)
Requires: jquery.js, jquery.sparkline.js
-->
<script type="text/javascript">
    $(document).ready(function() {
        $('#minichart').sparkline([10,8,5,7,4,4,1], {type: 'bar', barColor: 'green'});
    });
</script>
<div id="minichart">
    <!-- dynamic update by jquery -->
    <p>Please enable Javascript to view this sparkline widget.</p>
</div>
