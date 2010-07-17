<!--
Name: Local RSS Feed Reader
Description: Pulls in a local RSS feed (only works for local URLs, but allows client cert support)
Requires: jquery.js
-->
<script type="text/javascript">
$(document).ready(function() {
    $.get('/cert_redirect/demofeed.xml', function(doc) {
        $(".localfeed").html("");
	$(doc).find('item').each(function(index) {
            var html = "<div class='rssitem'><h3>" + $(this).find('title').text() + "</h3>";
            html += "<em class='rssdate'>" + $(this).find('pubDate').text() + "</em>";
            html += "<p class='rssdescription'>" + $(this).find('description').text() + "</p>";
            html += "<a href='" + $(this).find('link').text() + "' target='_blank'>View</a></div>";
            $('.localfeed').append(html);
            // show only first 3 entries
            if (index > 2) return false;
        });
    });
});
</script>
<div class="localfeed">
    <p>Please enable Javascript to view this local rssfeed widget.</p>
</div>
