<!--
Name: Daily Wulff-Morgenthaler Comic Strip
Author: Jonas Bardino <jonas DOT bardino AT gmail DOT com>
License: GPLv2
Description: Display daily WulffMorgenthaler comic strip
Requires: jquery.js
-->
<script type="text/javascript">
$(document).ready(function() {
    var today = new Date();
    /*
       we want YYYYMMDD and getMonth is zero-indexed but getDate is
       one-indexed. Both need to be zero padded for single digit
       values.
    */
    var url = "http://wulffmorgenthaler.dk/img/strip/WM_strip_DK_";
    url +=today.getFullYear();
    url += String("0" + (today.getMonth()+1)).slice(-2);
    url += String("0" + today.getDate()).slice(-2);
    url += ".jpg";
    $("#wulffmorgenthaler_comic").html('<img src="' + url + '" />');
});
</script>
<h4>Daily Wulff-Morgenthaler Comic Strip:</h4>
<div id="wulffmorgenthaler_comic">Please enable javascript for this
comic widget to work.</div>
