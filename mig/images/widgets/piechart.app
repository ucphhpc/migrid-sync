<!--
Name: Pie chart
Description: Pie chart using JQuery Google Charts plugin (modification
of default demo)
Requires: jquery.js, jquery.jgcharts.js
-->
<script type="text/javascript">
    $(document).ready(function() {
        var api = new jGCharts.Api();
        $("#piechart img").attr('src', api.make({data: [[153, 60, 52],
	[113, 70, 60], [120, 80, 40]],
                                                 type: 'p3',
                                                 size: '400x200'}));
    });
</script>
<div id="piechart">
    <!-- dynamic update by jquery -->
    <img src='' />
</div>
