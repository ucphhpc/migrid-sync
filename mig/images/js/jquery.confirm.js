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

function loadPageHelper(url) {
    /* 
       Helper to just open a new page ignoring any input args.
       Useful for generating a target function for runConfirmDialog when the
       target is just new page url.
    */
    return function(input) { window.location = url; }
}

function confirmDialog(target, text, textFieldName) {
    var link = "#";
    var input = {}; 
    if (target == undefined) {
	alert('internal error: confirm needs a target function!');
	target = loadPageHelper(window.location);
    }
    if (text == undefined) {
        text = "Are you sure?";
    }
    $( "#confirm_text").html(text);

    var addField = function() { /* doing nothing... */ };
    if (textFieldName != undefined) {
        $("#confirm_input").show();
        addField = function() {
	    input[textFieldName] = $("#confirm_input")[0].value;
        }
    }

    $( "#confirm_dialog").dialog("option", "buttons", {
              "No": function() { $("#confirm_input").hide();
                                 $("#confirm_text").empty();
                                 $("#confirm_dialog").dialog("close");
                               },
              "Yes": function() { addField();
                                  $("#confirm_input").hide();
                                  $("#confirm_text").empty();
                                  $("#confirm_dialog").dialog("close");
                                  target(input);
                                }
            });
    $( "#confirm_dialog").dialog("open");
}
