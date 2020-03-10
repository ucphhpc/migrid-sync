/*

  #
  # --- BEGIN_HEADER ---
  #
  # jquery.sitestatus - jquery site status helpers for static and user pages
  # Copyright (C) 2020  The MiG Project lead by Brian Vinter
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

/* Enable strict mode to help catch tricky errors early */
"use strict";


function fill_server_status_accordion(status_events, status_targets, locale) {
    /* Load content: roughly equivalent to $.get(url, data, success) */
    console.debug("AJAX fill server status accordion");
    $(status_targets["EN"]).html("<p class='leftpad spinner'>Loading status and news entries ...</p>");
    $(status_targets["DK"]).html("<p class='leftpad spinner'>Henter status og nyheder ...</p>");
    try {
        $.getJSON(status_events).done(function(response) {
            //console.debug("Success: "+response);
            var i;
            
            /* Loop through events */
            var en_items = [];
            var dk_items = [];
            var en_entry, en_title, en_workdatetimes, en_description, en_references;
            var dk_entry, dk_title, dk_workdatetimes, dk_description, dk_references;
            var work_start, work_end, announce_start, announce_end;
            var now = new Date();
            var work_dates = "";
            var work_datetimes = "";
            var title_class, workdatetimes_class, description_class, references_class;
            $.each(response, function (index, item) {
                en_entry = "";
                en_title = "";
                en_workdatetimes = "<b>Date:</b><br/>";
                en_description = "<b>Description:</b><br/>";
                en_references = "<b>References:</b><br/>";
                dk_entry = "";
                dk_title = "";
                dk_workdatetimes = "<b>Dato:</b><br/>";
                dk_description = "<b>Beskrivelse:</b><br/>";
                dk_references = "<b>Referencer:</b><br/>";
                title_class = "";
                workdatetimes_class = "";
                description_class = "";
                references_class = "hidden";
                work_start = work_end = new Date();
                announce_start = announce_end = new Date();
                $.each(item, function(key, val) {
                    if (key === "title") {
                        en_title = val["EN"];
                        dk_title = val["DK"];
                    }
                    else if (key === "description") {
                        en_description += val["EN"];
                        dk_description += val["DK"];
                    }
                    else if (key === "references") {
                        //console.debug("parse refs: "+val["EN"]+" : "+val["EN"].length);
                        /* Show references section */
                        references_class = references_class.replace("hidden", "");
                        for (i = 0; i < val["EN"].length; i++) {
                            en_references += "["+i+"] <a href='"+val["EN"][i]+"'>"+val["EN"][i]+"</a><br/>";
                        }
                        for (i = 0; i < val["DK"].length; i++) {
                            dk_references += "["+i+"] <a href='"+val["DK"][i]+"'>"+ val["DK"][i]+"</a><br/>";
                        }
                        //console.debug("parsed refs: "+en_references + " : " + dk_references);
                    }
                    else if (key === "work_start") {
                        work_start = new Date(val);
                    }
                    else if (key === "work_end") {
                        work_end = new Date(val);
                    }
                    else if (key === "announce_start") {
                        announce_start = new Date(val);
                    }
                    else if (key === "announce_end") {
                        announce_end = new Date(val);
                    }
                });
                
                if (work_start < now && now < work_end) {
                    title_class += "work warn iconleftpad";
                    //console.debug("show active: " + work_start +" < " +now+ " < "+work_end );

                } else if (announce_start < now && now < announce_end) {
                    title_class += "announce info iconleftpad";
                    //console.debug("announce ahead: " + announce_start +" < " +now+ " < "+announce_end );

                } else if (now < announce_start) {
                    //console.debug("skip future marker: " + announce_start + " vs "+now);
                    title_class += "waiting iconleftpad";
                } else if (now > announce_end) {
                    //console.debug("skip past marker: " + announce_end + " vs "+now);
                    title_class += "ok iconleftpad";
                }
                work_dates = work_start.toLocaleDateString(locale);
                if (work_end.toLocaleDateString(locale) != work_dates) {
                    work_dates += " - "+work_end.toLocaleDateString(locale);
                }
                work_datetimes = work_start.toLocaleString(locale);
                if (work_end.toLocaleString(locale) != work_datetimes) {
                    work_datetimes += " - "+work_end.toLocaleString(locale);
                }
                en_workdatetimes += work_datetimes;
                dk_workdatetimes += work_datetimes;

                /* NOTE: JQuery UI accordion maps hX-tags to titles with p-tags
                   as associated entries */
                en_entry = "<h4><span class='"+title_class+"'>"+work_dates+"</span>: "+en_title+"</h4><p><span class='"+workdatetimes_class+"'>" + en_workdatetimes +"</span><br/><span class='"+description_class+"'>" + en_description +"</span><br/><span class='"+references_class+"'>"+en_references+"</span></p>";
                en_items.push(en_entry);
                dk_entry = "<h4><span class='"+title_class+"'>"+work_dates+"</span>: "+dk_title+"</h4><p><span class='"+workdatetimes_class+"'>" + dk_workdatetimes +"</span><br/><span class='"+description_class+"'>" + dk_description + "</span><br/><span class='"+references_class+"'>"+dk_references+"</span></p>";
                dk_items.push(dk_entry);
                
            });
            $(status_targets["EN"]).html(en_items.join(""));
            $(status_targets["DK"]).html(dk_items.join(""));
            
            /* Call accordion init now that contents are loaded */
            delayed_init();
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
    var entry_systems = "";
    var entry_services = "";
    var outage_start, outage_end;
    var work_start, work_end;
    var announce_start, announce_end;
    var now = new Date();
    var time = now.toLocaleTimeString(locale);
    var outage_count = 0, warn_count = 0, announce_count = 0;

    $("#sitestatus-line").addClass("spinner").addClass("iconleftpad");
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
                var systems_overlap =  system_match.filter(function(n) {
                    return entry_systems.indexOf(n) !== -1;
                });
                if (system_match.indexOf('ALL') < 0 && systems_overlap.length < 1) {
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
                    announce_text += "<span class='"+entry_class+"'>"+entry_text+"</span><br/>";
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
                status_color = "green";
                status_caption = "PENDING";
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
            $("#sitestatus-line").removeClass("spinner").removeClass("iconleftpad");
            $("#sitestatus-line").html(status_line);
            $("#sitestatus-announce").removeClass("spinner");
            $("#sitestatus-announce").html(announce_text);

            console.debug("update server status complete");
        }).fail(function(response) {
            console.error("get status failed: "+ response);
            $("#sitestatus-line").removeClass("spinner");
            $("#sitestatus-line").html("Failed to dynamically load status information.");
        });
    } catch(err) {
        console.error("load json server status failed: "+err);
    }
}
