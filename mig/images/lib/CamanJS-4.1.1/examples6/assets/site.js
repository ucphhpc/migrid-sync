/* 
 *    Make sure we can always use console.log without scripts crashing. IE<=9
 *       does not init it unless in developer mode and things thus randomly fail
 *          without a trace.
 */

if (!window.console) {
  var noOp = function(){}; // no-op function
  console = {
    log: noOp,
    warn: noOp,
    error: noOp
  }
}



function pv_init_min_max_slider() {
    // http://refreshless.com/nouislider/
    
    $('#pv_min_max_slider').noUiSlider({
        start: [ 0, 255 ],
        connect: true,
        step: 1,
        range: {
            'min': 0,
            'max': 255,
        },    

        // Full number format support.
        //
        format: wNumb({
            mark: ',',
            decimals: 0
        }),
    });
 
    $('#pv_min_max_slider').Link('lower').to('-inline-<div class="tooltip"></div>', function ( value ) {

        // The tooltip HTML is 'this', so additional
        // markup can be inserted here.
        $(this).html(
            '<br>' +
            '<span id="pv_min_max_slider_min_value">' + value + '</span>'
        );
    });
    
    
    $('#pv_min_max_slider').Link('upper').to('-inline-<div class="tooltip"></div>', function ( value ) {

        // The tooltip HTML is 'this', so additional
        // markup can be inserted here.
        $(this).html(
            '<br>' +
            '<span id="pv_min_max_slider_max_value">' + value + '</span>'
            );
        });
    
    // http://refreshless.com/nouislider/events-callbacks/
   
    /* 
    $("#pv_min_max_slider").on({
        slide: function(){
            $("#l-slide").tShow(450);
        },
        set: function(){
            $("#l-set").tShow(450);
        },
        change: function(){
            $("#l-change").tShow(450);
        }
    });
    */
    $('#pv_min_max_slider').on('change', function() {
        var min_value = $('#pv_min_max_slider_min_value').text();
        var max_value = $('#pv_min_max_slider_max_value').text();
        console.log('DEBUG: change: ' + min_value + ' ' + max_value);

        var caman = Caman("#pv_image_canvas", function() {

            //this.resetOriginalPixelData();
            this.idmc_set_min_max_pixel_values(min_value, max_value);
            this.render();
        });

        // http://camanjs.com/guides/#AdvancedUsage
        Caman.Event.listen(caman, 'processComplete', function (job) {
          console.log("processComplete: ", job.name );
        });
        console.log("checkpoint");


        //source = "https://idmc.dk/cert_redirect/IDMC/data/.image/previews/h8_nos_1020.rec.DMP.png"; 
        //pv_image_load(source);
    }); 
    
}

function pv_image_load(url) {
    
    console.log("DEBUG: pv_image_load:  " + url);
    
    // $('#pv_image_canvas')[0] equals 
    // document.getElementById("pv_image_canvas");
    var canvas = $('#pv_image_canvas')[0];
    var context = canvas.getContext('2d');

    var imageObj = new Image();

     imageObj.onload = function() {
        context.clearRect(0, 0, canvas.width, canvas.height);
        context.drawImage(imageObj, 0, 0);
        Caman("#pv_image_canvas", function() {
            this.reloadCanvasData(); 
            this.idmc_set_original_pixeldata();
            this.render();
        });
     };
    imageObj.src = url;
}

/*
function pv_image_load(url) {
    Caman("#pv_image_canvas", url, function () {
        this.render();
    });
}
*/


function pv_init() {
    source = "https://idmc.dk/cert_redirect/IDMC/data/.image/previews/h8_nos_1020.rec.DMP.png"; 
    Caman("#pv_image_canvas", function() {
        pv_image_load(source);
        pv_init_min_max_slider();
    });

    //load_pv_image_canvas("../images/test1_640.jpg");
    //pv_init_CamanJS();
    //pv_image_load("../images/test1_640.jpg");
    //
}

$(document).ready(function() {
    pv_init();
});
