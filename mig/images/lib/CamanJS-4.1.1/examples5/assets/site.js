/* 
 *    Make sure we can always use console.log without scripts crashing. IE<=9
 *       does not init it unless in developer mode and things thus randomly fail
 *          without a trace.
 *          */
if (!window.console) {
  var noOp = function(){}; // no-op function
  console = {
    log: noOp,
    warn: noOp,
    error: noOp
  }
}

var cutoff_min_cutoff_mousemove = 0; 

function cutoff_min(e) {
    //var t = $(this);
    var slider_value =  $("#pv_filter_min_slider").val();
    
    //$(t).moiusemove( function(e) {
    console.debug('DEBUG event.type: ' + e.type);
    /*
    if( e.type == 'click' && cutoff_min_cutoff_mousemove == 0 || \
        (e.type == 'click' && e.buttons == 1 )) {
        //setTimeout(function() {
        console.log("DEBUG: " + slider_value);  
        $("#pv_filter_min_value").html(slider_value);
        //}, 1);
    }
//});
    */

    //console.log("DEBUG: " + slider_value);
    //$("#pv_filter_min_value").html(slider_value);
    /*
    console.log("debug: " + preview_image_id);
    cutoff_min_slider = document.getElementById("cutoff-min-slider");
    cutoff_min_text = document.getElementById("cutoff-min-text");
    console.log("debug: " + cutoff_min_slider.value);


    cutoff_min_text.textContent(cutoff_min_slider.value);
    */
    /*
    Caman(preview_image_id, function() {
        this.sunrise();
        this.render();
    });
    */
    return;
}

function init_cutoff_min() {
    var slider_value =  $("#pv_filter_min_slider").val();
     
    $("#pv_filter_min_value").html(slider_value);
   
    $("#pv_filter_min_slider").on("blur", function(e) {
        return cutoff_min(e);
    });
 
    /*    
    $("#pv_filter_min_slider").on("click", function(e) {
        return cutoff_min(e);
    });
    $("#pv_filter_min_slider").on("mousemove", function(e) {
        return cutoff_min(e);
    });
    */
}

function init() {
    //    console.log("DEBUG: " + $(".cutoff_min input[name='pv_min_slider']"));
    //console.log("DEBUG: " + $("#pv_filters .pv_filter_min .pv_filter_setting input[name='pv_min_slider']").val());
    init_cutoff_min();    
    
};

$(document).ready(function() {
    init();
});
