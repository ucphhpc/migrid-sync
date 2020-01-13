/*

  #
  # --- BEGIN_HEADER ---
  #
  # ui-v3_dynamic - dynamic helpers to fill support, about and status popups
  # Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

function init_quickstart_shared(intro_target, transfer_target, backup_target,
                                security_target) {
    console.log("init quickstart");
    if (intro_target) {
        $("#getting-started-en-button").click(function() {
            console.log("clicked getting started");
            window.open(intro_target);
        });
    }
    if (transfer_target) {
        $("#file-transfer-en-button").click(function() {
            window.open(transfer_target);
        });
    }
    if (backup_target) {
        $("#backup-en-button").click(function() {
            window.open(backup_target);
        });
    }
    if (security_target) {
        $("#security-en-button").click(function() {
            window.open(security_target);
        });
    }
}

function init_quickstart_static() {
    init_quickstart_shared("/public/user-guide.pdf", "", "", "");
    /* Make dynamic buttons inactive until logged in */
    $("div.quick-support.requires-login").prop('disabled', true).css('opacity', 0.5).css('cursor', 'default').prop('title', 'Please log in first to view specific feature help and setup');
    /*
      $("div.quick-support.requires-login").click(function() {
      //window.location.href="setup.py";
      show_login_msg('Please log in first to view specific feature help and setup');
      });
    */
}

function init_quickstart_dynamic() {
    init_quickstart_shared("http://www.erda.dk/public/ucph-erda-user-guide.pdf", 
                           "setup.py?topic=sftp", "setup.py?topic=duplicati",
                           "setup.py?topic=twofactor");
}

function init_faq() {
    console.log("init faq");
    /* Init FAQ as foldable but closed and with individual heights */
    $(".faq-entries.accordion").accordion({
        collapsible: true,
        active: false,
        heightStyle: "content"
    });
    /* fix and reduce accordion spacing */
    $(".ui-accordion-header").css("padding-top", 0).css("padding-bottom", 0).css("margin", 0);
}
function init_about() {
    console.log("init About");
}
function init_sitestatus() {
    /* NOTE: this point to the matched dom target when called from load */
    console.log("init sitestatus");
    //console.log("init sitestatus: "+$(this).html());
    var status_elem = $(this).find(".brief-status");
    //console.log("status_elem text: "+status_elem.text());
    //console.log("status_elem classes: "+status_elem.attr("class").toString());
    var status_title = "";
    var status_icon = "fa-question-circle";
    var status_color = "";
    var status_caption = ""
    var status_text = "";
    if (status_elem.hasClass("icon_online")) {
        status_icon = "fa-check-circle";
        status_color = "green";
        status_caption = "ONLINE";
    } else if (status_elem.hasClass("icon_offline")) {
        status_icon = "fa-exclamation-circle";
        status_color = "red";
        status_caption = "OFFLINE";
    } else {
        status_icon = "fa-exclamation-triangle";
        status_color = "orange";
        status_caption = "WARNING";
    }
    var start_date = new Date();
    var end_date = new Date();
    var now = new Date();
    var time = now.toLocaleTimeString();
    /* Use plain text of brief-status-english as main content */
    status_text += '<h3>Site Status</h3>';
    status_text += '<p id="sitestatus-text" class="status-text">'+status_elem.text()+'</p>';
    /* Use plain text of brief-announce-english as optional content */
    announce_text = ''
    $(this).find(".english .brief-announce").each(function(item) {
        elem_classes = $(this).attr("class").split(/\s+/);
        $.each(elem_classes, function(index, item) {
            if (item.startsWith('start_')) {
                //console.log("checking class: "+item);
                start_date = new Date(item.replace('start_', ''));
                //console.debug("found start date: "+start_date);
            } else if (item.startsWith('end_')) {
                //console.log("checking class: "+item);
                end_date = new Date(item.replace('end_', ''));
                //console.debug("found end date: "+end_date);
            }
        });
        if (start_date <= now && now <= end_date) {
            console.info("show active announce: "+start_date+":"+end_date);
            announce_text += '<p class="announce-text">'+$(this).text()+'</p>';
        } else {
            //console.debug("skip announce outside window: "+start_date+":"+end_date);
        }
    });
    if (announce_text) {
        status_text += '<h3>Recent News</h3>';
        status_text += announce_text;
        if (status_icon === "fa-check-circle") {
            status_icon = "fa-info-circle";
        }
    }
    /* Note: reuse 1.5rem size with ml-2 and mb-1 classes to mimic close */
    status_title += '<span id="sitestatus-icon" class="fas '+status_icon+' ml-2 mb-1" style="color: '+status_color+'; font-size: 1.5rem; float: left;"></span>';
    status_title += '<strong class="mr-auto text-primary" style="float: left;">'
    status_title += '<h3 style="margin-left: 5px;">'+status_caption+'</h3></strong>';
    status_title += '<small class="text-muted" style="float: right;"> at '+time+'</small>';
    $("#sitestatus-title").html(status_title);
    $("#sitestatus-content").html(status_text);
    /* replace default icon with actual status */
    $("#sitestatus-button").removeClass("fa-question-circle");
    /* TODO: remove this legacy icon removal once shared.html is updated */
    $("#sitestatus-button").removeClass("fa-info-circle");
    $("#sitestatus-button").addClass(status_icon);
    $("#sitestatus-button").css("color", status_color);
}

function load_quickstart_static(base_url) {
    /* Fetch quickstart contents from snippet specified in configuration */
    var content_url = base_url+" #quickstart-english";
    console.log("get content from "+content_url);
    /* Load content: roughly equivalent to $.get(url, data, success) */
    try {
        $("#quickstart-content").load(content_url, init_quickstart_static);
    } catch(err) {
        console.error("load quickstart failed: "+err);
    }
}
function load_quickstart_dynamic(base_url) {
    /* Fetch quickstart contents from snippet specified in configuration */
    var content_url = base_url+" #quickstart-english";
    console.log("get content from "+content_url);
    /* Load content: roughly equivalent to $.get(url, data, success) */
    try {
        $("#quickstart-content").load(content_url, init_quickstart_dynamic);
    } catch(err) {
        console.error("load quickstart failed: "+err);
    }
}
function load_faq(base_url) {
    /* Fetch FAQ contents from snippet specified in configuration */
    var content_url = base_url+" #faq-english";
    console.log("get content from "+content_url);
    /* Load content: roughly equivalent to $.get(url, data, success) */
    try {
        $("#faq-content").load(content_url, init_faq);
    } catch(err) {
        console.error("load faq failed: "+err);
    }
}
function load_about(base_url) {
    /* Fetch About contents from snippet specified in configuration */
    var content_url = base_url+" .english";
    console.log("get content from "+content_url);
    /* Load content: roughly equivalent to $.get(url, data, success) */
    try {
        $("#about-content").load(content_url, init_about);
    } catch(err) {
        console.error("load about failed: "+err);
    }
}
function load_sitestatus(base_url) {
    /* Fetch Sitestatus contents from snippet specified in configuration */
    var content_url = base_url+" .english";
    console.log("get content from "+content_url);
    /* Load content: roughly equivalent to $.get(url, data, success) */
    try {
        $("#sitestatus-content").load(content_url, init_sitestatus);
    } catch(err) {
        console.error("load sitestatus failed: "+err);
    }
}
