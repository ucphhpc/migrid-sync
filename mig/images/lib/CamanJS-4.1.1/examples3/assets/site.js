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

var preview_image_id = "#preview";

function cutoff_min(e) {
    console.log("debug: " + preview_image_id);
    cutoff_min_slider = document.getElementById("cutoff-min-slider");
    cutoff_min_text = document.getElementById("cutoff-min-text");
    console.log("debug: " + cutoff_min_slider.value);


    cutoff_min_text.textContent(cutoff_min_slider.value);
    /*
    Caman(preview_image_id, function() {
        this.sunrise();
        this.render();
    });
    */
    return;
}

function init() {
    cutoff_min_slider = document.getElementById("cutoff-min-slider");
    
    cutoff_min_slider.addEventListener("mouseup", function(e) {
        return cutoff_min(e);
    });
    
};

$(document).ready(function() {
    init();
});
