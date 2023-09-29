/*

  #
  # --- BEGIN_HEADER ---
  #
  # ui-dynamic - dynamic helpers to fill support, about and status content
  # Copyright (C) 2003-2021  The MiG Project lead by Brian Vinter
  #
  # This file is part of MiG.
  #
  # MiG is free software: you can redistribute it and/or modify
  # it under the terms of the GNU General Public License as published by
  # the Free Software Foundation; either version 2 of the License, or
  # (at your option) any later version.
  #
  # MiG is distributed in the hope that it will be useful,
  # but WITHOUT ANY WARRANTY; without even the implied warranty of
  # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  # GNU General Public License for more details.
  #
  # You should have received a copy of the GNU General Public License
  # along with this program; if not, write to the Free Software
  # Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
  #
  # -- END_HEADER ---
  #

*/

/* Language selector to trigger dynamic change of language on pages */

function switch_language(lang) {
    /* Hide all before showing only selected - use the built-in lang selector
       to match all accented versions like 'en' -> 'en', 'en-US', 'en-GB'
    */
    /* TODO: optimize this and use list of lang values */

    /* TODO: switch away from div-only lang and use i18n class instead */

    $("div:lang(en)").hide();
    $("div:lang(da)").hide();
    $(".i18n:lang(en)").hide();
    $(".i18n:lang(da)").hide();

    /* Use fade in to reduce flickering and improve rendering */
    var fade_time = 500;
    $("div:lang("+lang+")").fadeIn(fade_time);
    $(".i18n:lang("+lang+")").fadeIn(fade_time);
}

/* NOTE: extract browser/user language dynamically if possible */
function extract_default_lang() {
    return navigator.language || navigator.userLanguage || '';
}
function extract_default_locale() {
    var req_lang = extract_default_lang();
    return req_lang.split(/[_-]/)[0].toLowerCase();
}
function locale_to_country(locale) {
    if (locale === "da") {
        return "danish";
    } else if (locale === "en") {
        return "english";
    } else {
        return "english";
    }
}

/* Helper to lookup optional site-specific JS conf values with get_site_conf
   from site-conf.js with fall back to default_value if it is not available.
*/
function lookup_site_conf(key, default_value) {
    var value;
    try {
        value = get_site_conf(key);
        if (value === undefined) throw "get_site_conf "+key+" is undefined";
    } catch(err) {
        console.warn("failed to lookup " + key + " in site-conf.js: "+err);
        value = default_value;
    }
    //console.debug("looked up  " + key + " value " + value + " in site-conf.js");
    return value;
}

/* Load information snippets on-demand */

function init_quickstart_static() {
    /* NOTE: simply keep all site specific actions and targets in quickstart
       html snippet. We just use requires-login class markers to mark and
       distinguish static and dynamic content.
    */
    /* Show English content by default */
    $("#quickstart-english").show();
    /* Make dynamic buttons inactive until logged in */
    $("div.quick-support.requires-login").prop('disabled', true).css('opacity', 0.5).css('cursor', 'default').prop('title', 'Please log in first to view specific feature help and setup').prop("onclick", null);
}

function init_quickstart_dynamic() {
    /* NOTE: default logged in user - nothing special to do here */
    /* Show English content by default */
    $("#quickstart-english").show();
}
function init_quickstart(logged_in) {
    console.debug("init QuickStart");
    if (logged_in) {
        init_quickstart_dynamic();
    } else {
        init_quickstart_static();
    }
}
function init_faq() {
    console.debug("init FAQ");
    /* Init FAQ as foldable but closed and with individual heights */
    accordion_init(".faq-entries.accordion", false);
}
function init_support(logged_in) {
    console.debug("init Support");
    $(".snippet-disclaimer").remove();
    $("#support-content .privacytext").remove();
    init_quickstart(logged_in);
    init_faq();
    $("#support-english").show();
}
function init_about() {
    console.debug("init About");
    $(".snippet-disclaimer").remove();
    $("#about-english").show();
    $("#about-content .privacytext").show();
}
function init_tips() {
    console.debug("init Tips");
    $(".snippet-disclaimer").remove();
    /* Init Tips as single entry selected based on current date */
    $("#tips-content .tips-entries").hide();
    //console.debug("hiding all tips");
    $("#tips-content .tips-entry").hide();
    var now = new Date();
    /* NOTE: select day based on YYYYMMDD for consistent daily increment */
    var fulldate = now.getFullYear()*1E4 + now.getMonth()*1E2 + now.getDate();
    var total_tips = $("#tips-content .tips-entry").length;
    var show_tip = fulldate % total_tips
    console.debug("show tip number " + show_tip+" : "+fulldate+"%"+total_tips);
    $("#tips-content .tips-entry h4").each(function (index, title) {
        /* Prefix: tip title with Tip marker */
        //console.debug("found title: "+index);
        /* NOTE: leave a little room between fold icon and info icon */
        var title_text = "<span class='leftpad'></span>";
        title_text += "<span class='tip iconleftpad'>Quick Tip:</span> ";
        title_text += $(title).html() + " ... ";
        $(title).html(title_text);
    });
                                          
    $("#tips-content .tips-entry").each(function (index, item) {
        if (show_tip === index) {
            console.debug("show tip "+index);
            /* NOTE: chain loading marker removal to delay until visible */
            $(item).fadeIn(500, function() {
                $("#tips-content").removeClass("tips-loading");
            });
        }
    });
    /* NOTE: we need to specify header to look inside the div.tips-entry */
    accordion_init("#tips-content .tips-entries.accordion", false, "h4");
    $("#tips-content").removeClass("tips-placeholder");
    $("#tips-content .tips-entries").show();
    $("#tips-english").show();
}
function init_user_msg() {
    console.debug("init user messages");
    /* NOTE: we need to specify header to look inside the div.user-msg-entry */
    accordion_init("#user-msg-content .user-msg-entries.accordion", false, "h4");
    $("#user-msg-content .user-msg-entries").show();
 }

function load_support(base_url, logged_in) {
    /* Fetch Support contents from snippet on base_url */
    var content_url = base_url+" .english";
    console.debug("get content from "+content_url);
    /* Load content: roughly equivalent to $.get(url, data, success) */
    try {
        $("#support-content").load(content_url, function() {
            init_support(logged_in);
        });
    } catch(err) {
        console.error("load support failed: "+err);
    }
}
function load_about(base_url) {
    /* Fetch About contents from snippet on base_url */
    var content_url = base_url+" .english";
    console.debug("get content from "+content_url);
    /* Load content: roughly equivalent to $.get(url, data, success) */
    try {
        $("#about-content").load(content_url, init_about);
    } catch(err) {
        console.error("load about failed: "+err);
    }
}
function load_tips(base_url) {
    /* Fetch Tips contents from snippet on base_url */
    var content_url = base_url+" #tips-english";
    console.debug("get content from "+content_url);
    /* Load content: roughly equivalent to $.get(url, data, success) */
    try {
        $("#tips-content").addClass("tips-loading");
        $("#tips-content").load(content_url, init_tips);
    } catch(err) {
        console.error("load tips failed: "+err);
    }
}
function init_tips_content() {
    /* TODO: update to match init_tips if ever used */
    console.log("init tips");
    $(".snippet-disclaimer").remove();
}
function load_tips_content(base_url, country) {
    /* Fetch Tips contents from snippet on base_url */
    var content_url = base_url+" #tips-"+country;
    console.log("get content from "+content_url);
    /* Load content: roughly equivalent to $.get(url, data, success) */
    try {
        $("#tips-content-"+country).load(content_url, init_tips_content);
    } catch(err) {
        console.error("load "+country+" tips failed: "+err);
    }
}
function load_tips_lang_content(base_url, language_list) {
    /* Fetch Tips contents from base_url for for each lang in language_list */
    /* TODO: fetch base_url content only once and fill in turn? */
    console.log("get Tips lang content from "+base_url);
    for (let i = 0; i < language_list.length; i++) {
        load_tips_content(base_url, locale_to_country(language_list[i]));
    }
}
function load_sitestatus(base_url, system_match, locale) {
    /* Fetch and render Sitestatus contents from JSON events */
    var content_url = base_url;
    //console.debug("get content from "+content_url);
    fill_server_status_popup(content_url, system_match, locale);
}

/* NOTE: these about/support helpers are for legacy use on site front page */
function init_support_content(country) {
    console.log("init Suppport content");
    $(".snippet-disclaimer").remove();
    console.debug("distribute support section content: "+country);
    /* TODO: switch to dynamic detection of all content based on ID pattern */
    var sections = ["faq"];
    var content = '', anchor;
    for (let i = 0; i < sections.length; i++) {
        anchor = "#support-content-helper-"+country+" #"+sections[i]+"-"+country;
        console.debug("distribute support section content: "+anchor);
        content = $(anchor);
        console.debug("xfer section content: "+content);
        $("#support-content-"+country+"_"+sections[i]).html(content);
    }
    console.debug("clean up support helper");
    $("#support-content-helper-"+country).remove();
    /* Init FAQ accordion after inserting content */
    accordion_init(".faq-entries.accordion", false);
}
function load_support_content(base_url, country) {
    /* Fetch Support contents from snippet on base_url */
    var content_url = base_url+" #support-"+country;
    console.log("get content from "+content_url);
    /* Load content: roughly equivalent to $.get(url, data, success) */
    try {
        $("#support-content-helper-"+country).load(content_url, function() {
            init_support_content(country);
        });
    } catch(err) {
        console.error("load "+country+" support failed: "+err);
    }
}
function load_support_lang_content(base_url, language_list) {
    /* Fetch Support contents from base_url for for each lang in language_list */
    /* TODO: fetch base_url content only once and fill in turn? */
    console.log("get Support lang content from "+base_url);
    for (let i = 0; i < language_list.length; i++) {
        load_support_content(base_url, locale_to_country(language_list[i]));
    }
}
function init_about_content(country) {
    /* Distribute loaded content into sections */
    console.log("init About content");
    $(".snippet-disclaimer").remove();
    console.debug("distribute about section content: "+country);
    /* TODO: switch to dynamic detection of all content based on ID pattern */
    var sections = ["intro", "targetdata", "statusnews", "terms"];
    var content = '', anchor;
    for (let i = 0; i < sections.length; i++) {
        anchor = "#about-content-helper-"+country+" #"+sections[i]+"-"+country;
        console.debug("distribute about section content: "+anchor);
        content = $(anchor);
        console.debug("xfer section content: "+content);
        $("#about-content-"+country+"_"+sections[i]).html(content);
    }
    console.debug("clean up about helper");
    $("#about-content-helper-"+country).remove();
}
function load_about_content(base_url, country) {
    /* Fetch About contents from snippet on base_url */
    var content_url = base_url+" ."+country;
    console.log("get content from "+content_url);
    /* Load content: roughly equivalent to $.get(url, data, success) */
    try {
        $("#about-content-helper-"+country).load(content_url, function() {
            init_about_content(country);
        });
    } catch(err) {
        console.error("load "+country+" about failed: "+err);
    }
}
function load_about_lang_content(base_url, language_list) {
    /* Fetch About contents from base_url for for each lang in language_list */
    /* TODO: fetch base_url content only once and fill in turn? */
    console.log("get About lang content from "+base_url);
    for (let i = 0; i < language_list.length; i++) {
        load_about_content(base_url, locale_to_country(language_list[i]));
    }
}


/* We need to run accordion init as a callback on status event load */
function accordion_init(accordion_selector, active, header) {
    /* Init accordion as foldable, with active index entry open and with 
       individual heights. If active is false or left out it stays folded. */
    if (active === undefined) {
        active = false;
    }
    if (header === undefined) {
        header = "h4";
    }
    $(accordion_selector).accordion({
        collapsible: true,
        active: active,
        header: header,
        icons: {"header": "ui-icon-plus", "activeHeader": "ui-icon-minus"},
        heightStyle: "content"
    });
    /* fix and reduce accordion spacing */
    $(accordion_selector + " .ui-accordion-header").css("padding-top", 0).css("padding-bottom", 0).css("margin", 0);
}


/* Site status helpers */
function fill_server_status_accordion(status_events, brief_targets, status_targets, system_match, locale) {
    /* Load content: roughly equivalent to $.get(url, data, success) */
    console.debug("AJAX fill server status accordion");
    
    $(brief_targets["EN"]).html("Loading status ...").addClass("spinner iconleftpad");
    $(brief_targets["DK"]).html("Henter status ...").addClass("spinner iconleftpad");
    $(status_targets["EN"]).html("<p class='leftpad spinner'>Loading status and news entries ...</p>");
    $(status_targets["DK"]).html("<p class='leftpad spinner'>Henter status og nyheder ...</p>");
    
    var status_res = {"EN": "All systems and services are fully operational",
                      "DK": "Alle systemer og services kører planmæssigt",
                      "status_icon": "icon_online"};
    try {
        $.getJSON(status_events).done(function(response) {
            //console.debug("Success: "+response);
            var i;
            
            /* Loop through events */
            var en_items = [];
            var dk_items = [];
            var en_entry, en_title, en_workdatetimes, en_systems, en_services;
            var en_description, en_references, en_workdates;
            var dk_entry, dk_title, dk_workdatetimes, dk_systems, dk_services;
            var dk_description, dk_references, dk_workdates;
            var work_start, work_end, announce_start, announce_end, outage_start, outage_end;
            var entry_systems;
            var entry_services;
            var show_entry;
            var now = new Date();
            var work_dates = "";
            var work_datetimes = "";
            var active_announcements = 0;
            var title_class, workdatetimes_class, systems_class, services_class;
            var description_class, references_class;
            $.each(response, function (index, item) {
                en_entry = "";
                en_title = "";
                en_workdatetimes = "<b>Date:</b><br/>";
                en_workdates = "";
                en_systems = "<b>Systems:</b><br/>";
                en_services = "<b>Services:</b><br/>";
                en_description = "<b>Description:</b><br/>";
                en_references = "<b>References:</b><br/>";
                dk_entry = "";
                dk_title = "";
                dk_workdatetimes = "<b>Dato:</b><br/>";
                dk_workdates = "";
                dk_systems = "<b>Systemer:</b><br/>";
                dk_services = "<b>Services:</b><br/>";
                dk_description = "<b>Beskrivelse:</b><br/>";
                dk_references = "<b>Referencer:</b><br/>";
                title_class = "";
                workdatetimes_class = "";
                systems_class = "";
                services_class = "";
                description_class = "";
                references_class = "hidden";
                outage_start = outage_end = new Date();
                work_start = work_end = new Date();
                announce_start = announce_end = new Date();

                /* Show all except system-filtered entries here */ 
                show_entry = true; 
                $.each(item, function(key, val) {
                    if (key === "title") {
                        en_title = val["EN"];
                        dk_title = val["DK"];
                    } else if (key === "systems") {
                        entry_systems = val;
                        en_systems += val.join(", ");
                        dk_systems += val.join(", ").replace("ALL", "ALLE");
                    } else if (key === "services") {
                        entry_services = val;
                        en_services += val.join(", ");
                        dk_services += val.join(", ").replace("ALL", "ALLE");
                    } else if (key === "outage_start") {
                        outage_start = new Date(val);
                    } else if (key === "outage_end") {
                        outage_end = new Date(val);
                    } else if (key === "description") {
                        en_description += val["EN"];
                        dk_description += val["DK"];
                    } else if (key === "references") {
                        //console.debug("parse refs: "+val["EN"]+" : "+val["EN"].length);
                        /* Show references section */
                        for (i = 0; i < val["EN"].length; i++) {
                            en_references += "["+i+"] <a href='"+val["EN"][i]+"'>"+val["EN"][i]+"</a><br/>";
                        }
                        for (i = 0; i < val["DK"].length; i++) {
                            dk_references += "["+i+"] <a href='"+val["DK"][i]+"'>"+ val["DK"][i]+"</a><br/>";
                        }
                        if (val["EN"].length || val["DK"].length) {
                            references_class = references_class.replace("hidden", "");
                        }
                        //console.debug("parsed refs: "+en_references + " : " + dk_references);
                    } else if (key === "work_start") {
                        work_start = new Date(val);
                    } else if (key === "work_end") {
                        work_end = new Date(val);
                    } else if (key === "announce_start") {
                        announce_start = new Date(val);
                    } else if (key === "announce_end") {
                        announce_end = new Date(val);
                    }
                });
                
                /* Simple list intersection to check if systems lists overlap */
                var systems_overlap = entry_systems.filter(function(n) {
                    return (system_match.indexOf("ANY") !== -1 || system_match.indexOf(n) !== -1);
                });
                if (systems_overlap.length < 1) {
                    //console.debug("skip entry for "+entry_systems+" without match for "+system_match+", "+systems_overlap);
                    show_entry = false;
                } else if (outage_start < now && now < outage_end) {
                    title_class += "outage error iconleftpad";
                    //console.debug("show outage: " + outage_start +" < " +now+ " < "+outage_end);
                    status_res["status_icon"] = "icon_offline";
                    status_res["EN"] = "Active service outages";
                    status_res["DK"] = "Aktuelle serviceudfald";
                } else if (work_start < now && now < work_end) {
                    title_class += "work warn iconleftpad";
                    //console.debug("show active: " + work_start +" < " +now+ " < "+work_end);
                    if (status_res["status_icon"] != 'icon_offline') {
                        status_res["status_icon"] = "icon_slack";
                        status_res["EN"] = "Work tasks in progress";
                        status_res["DK"] = "Igangværende arbejdsopgaver";
                    }
                } else if (announce_start < now && now < announce_end) {
                    title_class += "announce info iconleftpad";
                    //console.debug("announce ahead: " + announce_start +" < " +now+ " < "+announce_end);
                    if (status_res["status_icon"] == 'icon_online') {
                        active_announcements += 1;
                    }
                } else if (now < announce_start) {
                    //console.debug("skip future marker: " + announce_start + " vs "+now);
                    title_class += "waiting iconleftpad";
                } else if (now > announce_end) {
                    //console.debug("skip past marker: " + announce_end + " vs "+now);
                    title_class += "ok iconleftpad";
                }
                work_dates = work_start.toLocaleDateString(locale);
                en_workdates = work_start.toLocaleDateString("en");
                dk_workdates = work_start.toLocaleDateString("da");
                if (work_end.toLocaleDateString(locale) != work_dates) {
                    work_dates += " - "+work_end.toLocaleDateString(locale);
                    en_workdates += " - "+work_end.toLocaleDateString("en");
                    dk_workdates += " - "+work_end.toLocaleDateString("da");
                }
                work_datetimes = work_start.toLocaleString(locale);
                en_workdatetimes += work_start.toLocaleString("en");
                dk_workdatetimes += work_start.toLocaleString("da");
                if (work_end.toLocaleString(locale) != work_datetimes) {
                    work_datetimes += " - "+work_end.toLocaleString(locale);
                    en_workdatetimes += " - "+work_end.toLocaleString("en");
                    dk_workdatetimes += " - "+work_end.toLocaleString("da");
                }

                if (show_entry) {
                    /* NOTE: JQuery UI accordion maps hX-tags to titles with p-tags
                       as associated entries */
                    en_entry = "<h4><span class='"+title_class+"'>"+en_workdates+"</span>: "+en_title+"</h4><p><span class='"+workdatetimes_class+"'>" + en_workdatetimes +"</span><br/><span class='"+systems_class+"'>" + en_systems +"</span><br/><span class='"+services_class+"'>" + en_services +"</span><br/><span class='"+description_class+"'>" + en_description +"</span><br/><span class='"+references_class+"'>"+en_references+"</span></p>";
                    en_items.push(en_entry);
                    dk_entry = "<h4><span class='"+title_class+"'>"+dk_workdates+"</span>: "+dk_title+"</h4><p><span class='"+workdatetimes_class+"'>" + dk_workdatetimes +"</span><br/><span class='"+systems_class+"'>" + dk_systems + "</span><br/><span class='"+services_class+"'>" + dk_services + "</span><br/><span class='"+description_class+"'>" + dk_description + "</span><br/><span class='"+references_class+"'>"+dk_references+"</span></p>";
                    dk_items.push(dk_entry);
                    //console.debug("include entry for "+entry_systems+" and match for "+system_match+" : "+systems_overlap);
                }
                
            });
            if (active_announcements > 0) {
                status_res["EN"] += ", with " + active_announcements + " active announcements";
                status_res["DK"] += ", med " + active_announcements + " aktuelle varsler";
            }
            $(brief_targets["EN"]).removeClass("spinner iconleftpad");
            $(brief_targets["DK"]).removeClass("spinner iconleftpad");
            $(brief_targets["EN"]).html(status_res["EN"]).addClass(status_res["status_icon"]);
            $(brief_targets["DK"]).html(status_res["DK"]).addClass(status_res["status_icon"]);
            $(status_targets["EN"]).html(en_items.join(""));
            $(status_targets["DK"]).html(dk_items.join(""));
            
            /* Call accordion init now that contents are loaded */
            accordion_init(".news-accordion", 0);
            console.debug("update server status complete");
        }).fail(function(response) {
            console.error("get status failed: "+ response);
        });
    } catch(err) {
        console.error("load json server status failed: "+err);
    }
}

function fill_server_status_popup(status_events, system_match, locale) {
    console.debug("AJAX fill server status popup from: "+status_events);
    var status_title = "";
    var status_icon = "fa-question-circle";
    var status_color = "";
    var status_caption = "";
    var status_line = "";
    var status_text = "";
    var announce_text = "";
    var show_entry = false;
    var entry_text = "";
    var entry_class = "";
    var entry_systems;
    var entry_services;
    var outage_start, outage_end;
    var work_start, work_end;
    var announce_start, announce_end;
    var now = new Date();
    var time = now.toLocaleTimeString(locale);
    var outage_count = 0, warn_count = 0, announce_count = 0;

    $("#sitestatus-line").addClass("spinner iconleftpad");
    $("#sitestatus-line").html("Loading status information ... please wait");
    try {
        $.getJSON(status_events).done(function(response) {
            //console.debug("Success: "+response);
            console.debug("update server status got response");
            var i;
            now = new Date();
            time = now.toLocaleTimeString(locale);
            $.each(response, function (index, item) {
                outage_start = outage_end = new Date();
                work_start = work_end = new Date();
                announce_start = announce_end = new Date();
                entry_text = "";
                entry_class = "";
                show_entry = false; 
                $.each(item, function(key, val) {
                    if (key === "title") {
                        entry_text = val["EN"];
                    } else if (key === "systems") {
                        entry_systems = val;
                    } else if (key === "services") {
                        entry_services = val;
                    } else if (key === "outage_start") {
                        outage_start = new Date(val);
                    } else if (key === "outage_end") {
                        outage_end = new Date(val);
                    } else if (key === "work_start") {
                        work_start = new Date(val);
                    } else if (key === "work_end") {
                        work_end = new Date(val);
                    } else if (key === "announce_start") {
                        announce_start = new Date(val);
                    } else if (key === "announce_end") {
                        announce_end = new Date(val);
                    }
                });
                
                /* Simple list intersection to check if systems lists overlap */
                var systems_overlap =  entry_systems.filter(function(n) {
                    return (system_match.indexOf("ANY") !== -1 || system_match.indexOf(n) !== -1);
                });
                if (systems_overlap.length < 1) {
                    //console.debug("skip entry for "+entry_systems+" without match for "+system_match+", "+systems_overlap);
                } else if (outage_start < now && now < outage_end) {
                    entry_class += "outage error iconleftpad";
                    console.debug("show error: " + outage_start +" < " +now+ " < "+outage_end);
                    outage_count += 1;                
                    show_entry = true;
                } else if (work_start < now && now < work_end) {
                    entry_class += "work warn iconleftpad";
                    console.debug("show active: " + work_start +" < " +now+ " < "+work_end);
                    warn_count += 1; 
                    show_entry = true;
                } else if (announce_start < now && now < announce_end) {
                    entry_class += "announce info iconleftpad";
                    console.debug("announce ahead: " + announce_start +" < " +now+ " < "+announce_end);
                    announce_count += 1; 
                    show_entry = true;
                } else if (now < announce_start) {
                    //console.debug("skip future marker: " + announce_start + " vs "+now);
                } else if (now > announce_end) {
                    //console.debug("skip past marker: " + announce_end + " vs "+now);
                }
                if (show_entry) {
                    //console.debug("include entry for "+entry_systems+" and match for "+system_match+" : "+systems_overlap);
                    announce_text += "<span class='"+entry_class+"'>"+work_start.toLocaleDateString(locale) + ": "+ entry_text + "</span><br/>";
                }
            });

            $("#sitestatus-recent").removeClass("hidden")
            if (outage_count > 0) {
                status_icon = "fa-exclamation-circle";
                status_color = "red";
                status_caption = "OUTAGE";
                status_line = "Currently one or more site services unavailable.";
            } else if (warn_count > 0) {
                status_icon = "fa-exclamation-triangle";
                status_color = "orange";
                status_caption = "WARNING";
                status_line = "Currently one or more active site service warnings.";
            } else if (announce_count > 0) {
                status_icon = "fa-info-circle";
                status_color = "orange";
                status_caption = "ANNOUNCED";
                status_line = "All site services online but pending notices.";
            } else {
                status_icon = "fa-check-circle";
                status_color = "green";
                status_caption = "ONLINE";
                status_line = "All site services are fully operational."
                $("#sitestatus-recent").addClass("hidden")
            }

            /* replace default icon with actual status: button and popup title */
            $("#sitestatus-button").removeClass("fa-question-circle");
            $("#sitestatus-button").addClass(status_icon);
            $("#sitestatus-button").css("color", status_color);
            $("#sitestatus-icon").removeClass("fa-question-circle");
            $("#sitestatus-icon").addClass(status_icon);
            $("#sitestatus-icon").css("color", status_color);
            $("#sitestatus-caption").html(status_caption);
            $("#sitestatus-timestamp").html("at "+time);
            $("#sitestatus-line").removeClass("spinner iconleftpad");
            $("#sitestatus-line").html(status_line);
            $("#sitestatus-announce").removeClass("spinner iconleftpad");
            $("#sitestatus-announce").html(announce_text);

            console.debug("update server status complete");
        }).fail(function(response) {
            console.error("get status failed: "+ response);
            $("#sitestatus-line").removeClass("spinner iconleftpad");
            $("#sitestatus-line").html("Failed to dynamically load status information.");
        });
    } catch(err) {
        console.error("load json server status failed: "+err);
    }
}
