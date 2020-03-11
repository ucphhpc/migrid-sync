/* 
   Local site variables to adjust look n' feel of what is displayed on the 
   'static' html pages with javascript content loading on this site.

*/
function get_site_conf(key) {
    var value;
    if (key === 'content_url') {
        value = "status-events.json";
    } else if (key === 'system_match') {
        value = ["ALL", "ERDA", "IDMC", "SIF"];
    } 
    return value;
}
