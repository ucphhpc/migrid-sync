/* 
   Local site variables to adjust look n' feel of what is displayed on the 
   'static' html pages with javascript content loading on this site.

   IMPORTANT: ui doubles as status.erda.dk so we should only display production
              information for all official sites in status.html here.
*/
function get_site_conf(key) {
    var value;
    if (key === 'content_url') {
        value = "status-events.json";
    } else if (key === 'system_match') {
        /* We keep IDMC for history */
        value = ["ALL", "ERDA", "SIF", "MiGrid", "IDMC"];
    } else if (key === 'auth_methods') {
        value = ["extoid", "extoidc", "migoid", "extcert"];
    } 
    return value;
}
