/*

#
# --- BEGIN_HEADER ---
#
# jquery.confirm - jquery based confirm dialog
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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

/*

    MiG common confirm action dialog helper

    Provides a confirmDialog(target, text, textFieldName) function where
    target is a javascript function called if the user answers confirms.
    It takes a variable dictionary as input in order to support passing
    additional variables. The text and textFieldName arguments are optional
    and if supplied, text is inserted as the dialog message. If textFieldName
    is provided an input field is shown and the value gets passed on to target
    with that name.

    The loadPageHelper helper function is supplied in order to make it easy to
    generate a simple page load target function.

    Expects a JQuery UI dialog on a form like:

    <div id="confirm_dialog" title="Confirm" style="background:#fff;">
        <div id="confirm_text"><!-- filled by js --></div>
        <textarea cols="40" rows="4" id="confirm_input" style="display:none;"/></textarea>
    </div>

*/

/* Enable strict mode to help catch tricky errors early */
"use strict";

function loadPageHelper(url) {
    /*
       Helper to just open a new page ignoring any input args.
       Useful for generating a target function for runConfirmDialog when the
       target is just new page url.
    */
    return function (input) {
        window.location = url;
    };
}

function confirmDialog(target, text, textFieldName) {
    var input = {};
    if (target === undefined) {
        alert("internal error: confirm needs a target function!");
        target = loadPageHelper(window.location);
    }
    if (text === undefined) {
        text = "Are you sure?";
    }
    $("#confirm_text").html(text);

    var addField = function () {
        /* doing nothing... */
        return;
    };
    if (textFieldName !== undefined) {
        $("#confirm_input").show();
        addField = function () {
            input[textFieldName] = $("#confirm_input")[0].value;
        };
    }

    $("#confirm_dialog").dialog("option", "buttons", {
        "No": function () {
            $("#confirm_input").hide();
            $("#confirm_text").empty();
            $("#confirm_dialog").dialog("close");
        },
        "Yes": function () {
            addField();
            $("#confirm_input").hide();
            $("#confirm_text").empty();
            $("#confirm_dialog").dialog("close");
            target(input);
        }
    });
    $("#confirm_dialog").dialog("open");
}
