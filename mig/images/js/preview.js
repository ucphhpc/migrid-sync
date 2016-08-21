/*
#
# --- BEGIN_HEADER ---
#
# preview - javascript based image preview library
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
#
# This file is part of MiG.
#
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public Licethnse as published by
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
    
Preview = function (layout, options, debug) {
	//console.debug('Preview: constructor: ' + selfname);
    console.debug('Preview: constructor');
    var _this = this;
    _this.settings = {
        layout: layout,
        options: options,
        debug: debug,
        paraview: false,
        volume: false,
        caman: false,
        visible: false,
        height: 0,
        zoom: 0,
        min_zoom: 0,
        max_zoom: 2, 
        last_zoom: 0,
    };

    var callback = function() {
        var max_decimals = _this.get_format_decimals();
        _this.caman = new PreviewCaman(max_decimals, debug);
        _this.paraview = new PreviewParaview(debug);    
    }
    _this.init_html(callback);
}

/*
// For Paraview DEBUG
setTimeout(function() { 
    console.debug('starting paraview');
    toggle_paraview();
}, 1000); 
    // End: For Paraview DEBUG
*/

Preview.prototype.debug_js_object = function (js_object) {
    console.debug('debug_js_object: ');
    console.debug(JSON.stringify(js_object).split(",").join("'\n").split(":").join(": '").split("}").join("'}"));
    console.debug('end debug_js_object: ');
}

Preview.prototype.init_html = function(callback) {
    var html_out = '<input type="hidden" value="" name="fm_preview_base_path" />';
    html_out += '<input type="hidden" value="" name="fm_preview_path" />';
    html_out += '<input type="hidden" value="" name="fm_preview_filename" />';
    html_out += '<input type="hidden" value="" name="fm_preview_extension" />';
    html_out += '<div id="fm_preview_menubar" class="fm_preview_menubar">';
    html_out += '   <div id="fm_preview_menubar_refresh" class="fm_preview_menubar_entry" title="Refresh Preview">';
    html_out += '       <img src="/images/icons/arrow_refresh.png">';
    html_out += '   </div>';
    html_out += '   <div id="fm_preview_menubar_zoom_in" class="fm_preview_menubar_entry" title="Zoom In">';
    html_out += '       <img src="/images/icons/add.png">';
    html_out += '   </div>';
    html_out += '   <div id="fm_preview_menubar_zoom_out" class="fm_preview_menubar_entry" title="Zoom Out">';
    html_out += '       <img src="/images/icons/delete.png">';
    html_out += '   </div>';
    html_out += '   <div id="fm_preview_menubar_paraview" class="fm_preview_menubar_entry" title="Toggle Volume">';
    html_out += '       <img src="/images/icons/paraview.png">';
    html_out += '   </div>';
    html_out += '</div>';
    html_out += '<div id="fm_preview_caman" class="fm_preview_caman">';
    html_out += '   <div id="fm_preview_left_tile" class="fm_preview_left_tile">';
    html_out += '       <div id="fm_preview_left_tile_histogram">';
    html_out += '           <canvas id="fm_preview_histogram_image"></canvas>';
    html_out += '       </div>';
    html_out += '       <div id="fm_preview_left_tile_histogram_actions">';
    html_out += '           <div id="fm_preview_histogram_min_max_slider"></div>   ';
    html_out += '           <br>';
    html_out += '           <button id="preview_histogram_reset_button" title="Reset sliders">Reset</button>';
    html_out += '           <button id="preview_histogram_set_cutoff_button" title="Set preview cutoff based on sliders">Set Cutoff</button>';
    html_out += '           <!-- <button id="preview_histogram_auto_button">Auto</button> -->';
    html_out += '       </div>';
    html_out += '       <div id="fm_preview_left_output">';
    html_out += '           <!-- this is a placeholder for contents: do not remove! -->';
    html_out += '       </div>';
    html_out += '   </div>';
    html_out += '   <div id="fm_preview_center_tile" class="fm_preview_center_tile">';
    html_out += '       <canvas id="fm_preview_image"></canvas>';
    html_out += '   </div>';
    html_out += '   <div id="fm_preview_right_tile" class="fm_preview_right_tile">';
    html_out += '       <div id="fm_preview_right_output">';
    html_out += '           <!-- this is a placeholder for contents: do not remove! -->';
    html_out += '       </div>';
    html_out += '   </div>';
    html_out += '</div>';
    html_out += '<div id="fm_preview_paraview" class="fm_preview_paraview">';
    html_out += '   <!-- this is a placeholder for contents: do not remove! -->';
    html_out += '</div>';

    if(typeof callback === "function"){
        $("#fm_previews").html(html_out).promise().done(callback);
    } else {
        $("#fm_previews").html(html_out);
    }
}

Preview.prototype.init_tiles_HTML = function(image_meta) {
    var right_html_out = '';
    var left_html_out = '';
    var image_filepath;
    var image_path;

    $(".fm_previews input[name=fm_preview_base_path]").val(image_meta.base_path);
    $(".fm_previews input[name=fm_preview_path]").val(image_meta.path);
    $(".fm_previews input[name=fm_preview_filename]").val(image_meta.name);
    $(".fm_previews input[name=fm_preview_extension]").val(image_meta.extension);

    preview_image_url = image_meta.preview_image_url;

    if (image_meta.path === '') {
        image_path = image_meta.base_path;
    }
    else {
        image_path = image_meta.base_path + image_meta.path +  "/";
    }
    image_filepath = image_path + image_meta.name;

    right_html_out  += '<p>Image: ' + image_filepath + '</p>'
        + '<p>Image Type: ' + image_meta.image_type + '</p>'
        + '<p>Data Type: ' + image_meta.data_type + '</p>'
        + '<p>Offset: ' + image_meta.offset + '</p>'
        + '<p>X Dimension: ' + image_meta.x_dimension + '</p>'
        + '<p>Y Dimension: ' + image_meta.y_dimension + '</p>'
        + '<p>Min Value: ' + Number(image_meta.min_value).toExponential(this.get_format_decimals()) + '</p>'
        + '<p>Max Value: ' + Number(image_meta.max_value).toExponential(this.get_format_decimals()) + '</p>'
        + '<p>Mean Value: '  + Number(image_meta.mean_value).toExponential(this.get_format_decimals()) + '</p>'
        + '<p>Median Value: ' + Number(image_meta.median_value).toExponential(this.get_format_decimals()) + '</p>';

    // TODO: Move input fields HTML to fileman.py ?

    left_html_out += '<input type="hidden" value="' + image_meta.preview_cutoff_min + '" name="cutoff_min_value" />' 
        + '<input type="hidden" value="' + image_meta.preview_cutoff_max + '" name="cutoff_max_value" />' 
        + '<input type="hidden" value="' + image_meta.preview_cutoff_min + '" name="current_min_value" />' 
        + '<input type="hidden" value="' + image_meta.preview_cutoff_max + '" name="current_max_value" />' 
        + '<input type="hidden" value="' + image_meta.preview_image_scale + '" name="scale_value" />' 
        + '<p><span id="fm_preview_left_output_min_value_show"></span></p>' 
        + '<p><span id="fm_preview_left_output_max_value_show"></span></p>' 
        + '<p><span id="fm_preview_left_output_preview_image_scale_value_show"></span></p>'

    $("#fm_preview_right_output").html(right_html_out);
    $("#fm_preview_left_output").html(left_html_out);
}

Preview.prototype.update_fm_layout = function(layout) {    
    var fileManagerInnerHeight = layout.fm.innerHeight;
    var fileFolderInnerHeight = layout.fm.fileFolderInnerHeight;
    var previewInnerHeight = 0;
    var previewInnerHeightFrac = 0.50;
    var centerTileWidthFrac = 0.40;
    var previewWidth = $("#fm_filemanager .fm_previews").outerWidth() 
    var previewInnerWidth = $("#fm_filemanager .fm_previews").width() 
        - $("#fm_filemanager .fm_preview_menubar").outerWidth();
    var previewCenterTileWidth = Math.floor(previewInnerWidth * centerTileWidthFrac);
    var previewLeftTileWidth = Math.floor((previewInnerWidth - previewCenterTileWidth)/2);
    var previewRightTileWidth = previewLeftTileWidth;

   
    if (this.settings.zoom == 0) {
        previewInnerHeight = 0;
        fileFolderInnerHeight = fileManagerInnerHeight;    
    }
    else if (this.settings.zoom == 1) {
        previewInnerHeight = fileFolderInnerHeight * previewInnerHeightFrac;

        fileFolderInnerHeight = fileManagerInnerHeight - previewInnerHeight;
    }
    else if (this.settings.zoom > 1) {
        previewInnerHeight = fileManagerInnerHeight;
        fileFolderInnerHeight = 0;
    }

    layout.fm.fileFolderInnerHeight = fileFolderInnerHeight;
    layout.fm.preview = {
        width: previewWidth,
        innerHeight: previewInnerHeight,
        innerWidth: previewInnerWidth,
        leftTileWidth: previewLeftTileWidth,
        centerTileWidth: previewCenterTileWidth,
        rightTileWidth: previewRightTileWidth
    };
    return layout;
}
       
Preview.prototype.update_html_layout = function(callback) {
    var layout = (typeof this.settings.layout === "function") ?
        _this.settings.layout() : 
        _this.settings.layout;
    $("#fm_filemanager .fm_previews").css("height", layout.fm.preview.innerHeight + "px");
    $("#fm_filemanager .fm_preview_caman").css("width", layout.fm.preview.innerWidth + "px");
    $("#fm_filemanager .fm_preview_left_tile").css("width", layout.fm.preview.leftTileWidth + "px");
    $("#fm_filemanager .fm_preview_center_tile").css("width", layout.fm.preview.centerTileWidth + "px");
    $("#fm_filemanager .fm_preview_right_tile").css("width", layout.fm.preview.rightTileWidth + "px");
    $("#fm_filemanager .fm_preview_paraview").css("width", layout.fm.preview.innerWidth + "px");
    $("#fm_filemanager .pv-viewport").css("width", layout.fm.preview.innerWidth + "px");
}

Preview.prototype.init_image_settings = function(image_settings, image_meta, volume_meta) {
    
    // Check if preview files are ready

    if (image_settings.image_settings_status.toLowerCase() == 'ready' ) {
        $("#preview_histogram_set_cutoff_button").attr('disabled', false);
    } else {
        $("#preview_histogram_set_cutoff_button").attr('disabled', true);

    }


    // Check if preview volumes are ready
    
    if (volume_meta != null && image_settings.volume_settings_status.toLowerCase() == 'ready') {
        this.paraview.set_volume_xdmf(volume_meta.preview_xdmf_filepath);
        $("#fm_preview_menubar_paraview").css('opacity', 1.0);
        this.settings.volume = true;
    } else {
        $("#fm_preview_menubar_paraview").css('opacity', 0.5);
        this.settings.volume = false;
        console.debug('volume_meta is null or _NOT_ ready');
    }
}

Preview.prototype.bind_buttons = function() {
    var _this = this;
    $("#fm_preview_menubar_zoom_out").on('click',
        function(event) {
            console.debug('fm_preview_menubar_zoom_out');
            _this.zoom_out();
        });

    $("#fm_preview_menubar_zoom_in").on('click',
        function(event) {
            console.debug('fm_preview_menubar_zoom_in');
            _this.zoom_in();
        });

    $("#fm_preview_menubar_refresh").on('click',
        function(event) {
            console.debug('fm_preview_menubar_refresh');
            _this.refresh();
        });

    $("#fm_preview_menubar_paraview").on('click',
        function(event) {
            console.debug('fm_preview_menubar_paraview');
            _this.toggle_paraview();
        });

    $("#preview_histogram_reset_button").on('click',
        function(event) {
            _this.caman.reset();
        });

    $("#preview_histogram_set_cutoff_button").on('click',
        function(event) {

            // Disable button

            $("#preview_histogram_set_cutoff_button").attr('disabled', true);

            var path = $(".fm_previews input[name=fm_preview_base_path]").val();
            var extension = $(".fm_previews input[name=fm_preview_extension]").val();
            var min_value = $("#fm_preview_left_output input[name='current_min_value']").val();
            var max_value = $("#fm_preview_left_output input[name='current_max_value']").val();

            var error_callback = function(errors) {
                $("#fm_preview_left_output").html(errors);
                console.error(errors);
            }
        
            var warning_callback = function(warnings) {
                $("#fm_preview_left_output").html(warnings);
                console.warn(warnings);
            }

            var ok_callback = function(image_setting, image_meta, volume_meta) {
                console.debug('preview_histogram_set_cutoff_button OK');
            }
            _this.update_image_dir(path,
                                   extension,
                                   min_value,
                                   max_value,
                                   ok_callback, 
                                   error_callback, 
                                   warning_callback);
        }
    );
}                                           

Preview.prototype.get_preview_histogram_data = function(image_meta) {
    return new Uint32Array(image_meta.preview_histogram);
}

Preview.prototype.get_format_decimals = function() {
    var format_decimals = 4;

    return format_decimals;
}

Preview.prototype.open = function(path) {
    // Disable content depending buttons by default
    var _this = this;

    var error_callback = function(errors) {
        $("#fm_preview_right_output").html(errors);
        $("#fm_preview_left_output").html('');
        console.error(errors);
    }
    var warning_callback = function(warnings) {
        $("#fm_preview_right_output").html(warnings);
        $("#fm_preview_left_output").html('');
        console.warn(warnings);
    }
    var ok_callback = function(image_setting, image_meta, volume_meta) {
        var preview_histogram = _this.get_preview_histogram_data(image_meta);
        _this.init_tiles_HTML(image_meta);
        _this.init_image_settings(image_setting, image_meta, volume_meta);
        _this.caman.set_histogram_data(preview_histogram);
        _this.settings.zoom = 1;
        _this.settings.caman = true;
        _this.show(function() {
            _this.caman.load(image_meta.preview_image_url);
        });
    }
    _this.get_image_file(path, ok_callback, error_callback, warning_callback);
}

Preview.prototype.close = function() {
    this.paraview.close();
}

Preview.prototype.refresh = function(callback) {
    var _this = this;
    console.debug('refresh callback: ' + callback);

    var refresh_callback = function() {
        console.debug('refresh_callback: zoom: ' + _this.settings.zoom + ', caman: ' + _this.settings.caman + ', paraview: ' + _this.settings.paraview);
        _this.caman.refresh(_this.settings.caman, callback);
        _this.paraview.refresh(_this.settings.paraview, callback);
    }
    _this.show(refresh_callback);
}

Preview.prototype.zoom_out = function(callback) {
    console.debug('zoom_out: paraview: ' + this.settings.paraview);
    console.debug('zoom_out: caman: ' + this.settings.caman);
    console.debug('zoom_out: zoom: ' + this.settings.zoom);
    if (this.settings.paraview  == true) {
        this.toggle_paraview(callback);
    }
    else if (this.settings.caman == true) {
        if (this.settings.zoom > this.settings.min_zoom) {
            this.settings.last_zoom = this.settings.zoom;
            this.settings.zoom -= 1;
            if (this.settings.zoom == this.settings.min_zoom) {
                this.settings.caman = false;    
            } 
            console.debug('zoom_out check: paraview: ' + this.settings.paraview);
            console.debug('zoom_out check: caman: ' + this.settings.caman);
            console.debug('zoom_out check: zoom: ' + this.settings.zoom);
            this.refresh(callback);
        }
    }
}

Preview.prototype.zoom_in = function(callback) {
    if (this.settings.paraview == false && 
        this.settings.zoom < this.settings.max_zoom) {
            this.settings.caman = true;
            this.settings.last_zoom = this.settings.zoom;
            this.settings.zoom += 1;
            this.refresh(callback);
    }
}

Preview.prototype.set_visibility_left_tile = function(visibility) {
    $("#fm_preview_left_tile").css("visibility", visibility);
    $("#fm_preview_left_tile_histogram").css("visibility", visibility);
    $("#fm_preview_left_tile_histogram_actions").css("visibility", visibility);
    $("#fm_preview_left_output").css("visibility", visibility);
}

Preview.prototype.set_visibility_center_tile = function(visibility) {
    $("#fm_preview_center_tile").css("visibility", visibility);
}

Preview.prototype.set_visibility_right_tile = function(visibility) {
    $("#fm_preview_right_tile").css("visibility", visibility);
    $("#fm_preview_right_output").css("visibility", visibility);
}

Preview.prototype.set_visibility_caman = function(visibility) {
    $("#fm_preview_caman").css('visibility', visibility);
    this.set_visibility_left_tile(visibility);
    this.set_visibility_center_tile(visibility);
    this.set_visibility_right_tile(visibility);
}  
Preview.prototype.set_visibility_paraview = function(visibility) {
    $("#fm_preview_paraview").css('visibility', visibility);
}  

Preview.prototype.set_visibility = function(visibility) {
    $("#fm_preview_menubar").css('visibility', visibility);
    var caman_visibility;
    var paraview_visibility;

    if (this.settings.paraview == false) {
        $("#fm_preview_caman").css('height', '100%');
        $("#fm_preview_paraview").css('height', '0%');
        caman_visibility = visibility;
        paraview_visibility = 'hidden';
    }
    else {
        caman_visibility = 'hidden';
        $("#fm_preview_caman").css('height', '0%');
        $("#fm_preview_paraview").css('height', '100%');
        paraview_visibility = visibility;
    }

    this.set_visibility_caman(caman_visibility);
    this.set_visibility_paraview(paraview_visibility);
}   

Preview.prototype.show = function(callback) {
    var _this = this;
    var layout = (typeof this.settings.layout === "function") ?
        _this.settings.layout() : 
        _this.settings.layout;
    //console.debug('layout: ' + Object.keys(layout));
    //_this.debug_js_object(layout);
    /*for (var key in Object.keys(layout)) {
        console.debug('layout -> ' + key + ' : ' + layout[key]);
    }
    */
    console.debug('preview show');
    

    var visibility = (_this.settings.zoom == 0) ? 
        'hidden' :
        'visible';
    var animate_speed = (_this.settings.zoom < _this.settings.last_zoom) ?
        _this.settings.options.collapseSpeed :
        _this.settings.options.expandSpeed;
    var animate_easing = (_this.settings.zoom < _this.settings.last_zoom) ?
        _this.settings.options.collapseEasing :
        _this.settings.options.expandEasing;
    $("#fm_filemanager .fm_folders").animate(
        {height: layout.fm.fileFolderInnerHeight + 'px'},
        {duration: animate_speed,
        easing: animate_easing});
    $("#fm_filemanager .fm_files").animate(
        {height: layout.fm.fileFolderInnerHeight + 'px'},
        {duration: animate_speed,
        easing: animate_easing});
    $("#fm_filemanager .fm_preview_caman").css("width", layout.fm.preview.innerWidth + "px");
    $("#fm_filemanager .fm_preview_left_tile").css("width", layout.fm.preview.leftTileWidth + "px");
    $("#fm_filemanager .fm_preview_center_tile").css("width", layout.fm.preview.centerTileWidth + "px");
    $("#fm_filemanager .fm_preview_right_tile").css("width", layout.fm.preview.rightTileWidth + "px");
    $("#fm_filemanager .fm_preview_paraview").css("width", layout.fm.preview.innerWidth + "px");
    $("#fm_filemanager .fm_previews").animate(
        {height: layout.fm.preview.innerHeight + 'px'},
        {duration: animate_speed,
        easing: animate_easing,
        complete: function() {  
            _this.set_visibility(visibility);
            if (typeof callback === "function") {
                console.debug('show callback called: ' + callback);
                callback();
            }
        }});
}

Preview.prototype.toggle_paraview = function(callback) {
    
    console.debug('toggle_paraview');
    if (this.settings.volume == true) {
        if (this.settings.paraview == true) {
            this.settings.paraview = false;
            this.settings.caman = true;
            this.settings.zoom = this.settings.last_zoom;
            //this.paraview.close();
        }
        else {
            this.settings.paraview = true;
            this.settings.caman = false;
            this.settings.last_zoom = this.settings.zoom;
            this.settings.zoom = this.settings.max_zoom;
            //callback = $.proxy(this.paraview.open, this.paraview);
        }
        
        // TODO: Make contrast slider for volume instead of using the min/max from sliced view

        var min_value = $("#fm_preview_left_output input[name='current_min_value']").val();
        var max_value = $("#fm_preview_left_output input[name='current_max_value']").val();

        var refresh_proxy = $.proxy(this.refresh, this, callback);
        
        console.debug('toggle_paraview zoom: ' + this.settings.zoom);
        this.paraview.set_value_range(min_value, max_value, refresh_proxy); 
    }    
}

Preview.prototype.get_image_file = function(path, ok_callback, error_callback, warning_callback) {
    console.debug('get_image_file -> path: ' + path);

    $.ajax({
        url: 'filemetaio.py',
        data: { path: path,
                output_format: 'json',
                action: 'get_file',
                flags: 'i',
              },
        type: "GET",
        dataType: "json",
        cache: false,
        success: function(jsonRes, textStatus) {
            var i;
            var errors = $(this).renderError(jsonRes);
            var warnings = $(this).renderWarning(jsonRes);
            var image_settings = null;
            var image_meta = null;
            var volume_meta = null;

            for (i = 0; i < jsonRes.length; i++) {
                if (jsonRes[i].object_type == 'image_setting') {
                    image_setting = jsonRes[i];
                } else if (jsonRes[i].object_type == 'image_meta') {
                    image_meta = jsonRes[i];
                } else if (jsonRes[i].object_type == 'volume_meta') {
                    volume_meta = jsonRes[i];
                }
            }
            if (errors.length > 0) {
                if (typeof error_callback === "function") {
                    console.error(errors);
                } else {
                    error_callback(errors);
                }
                
            } else if (warnings.length > 0) {
                if (typeof warning_callback === "function") {
                    console.warn(warnings);
                } else {
                    warning_callback(warnings);
                }                    
            } else {
                if (typeof ok_callback === "function") {
                    ok_callback(image_setting, image_meta, volume_meta);
                }
            }
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error("get_image_file error: " + errorThrown);
        }
    });
}


Preview.prototype.get_image_dir = function(
                                        path, 
                                        extension, 
                                        ok_callback,
                                        error_callback,
                                        warning_callback) {

    console.debug('get_image_dir -> path: ' + path + ', extension: ' + extension);
    $.ajax({
        url: 'filemetaio.py',
        data: { path: path,
                extension: extension,
                output_format: 'json',
                action: 'get_dir',
                flags: 'i',
              },
        type: "GET",
        dataType: "json",
        cache: false,
        success: function(jsonRes, textStatus) {
            var i;
            var errors = $(this).renderError(jsonRes);
            var warnings = $(this).renderWarning(jsonRes);
            var image_setting = null;
            for (i = 0; i < jsonRes.length; i++) {
                if (jsonRes[i].object_type == 'image_setting') {
                    image_setting = jsonRes[i];
                }
            }

            if (errors.length > 0) {
                if (typeof error_callback === "function") {
                    console.error(errors);
                } else {
                    error_callback(errors);
                }                
            } else if (warnings.length > 0) {
                if (typeof warning_callback === "function") {
                    console.warn(warnings);
                } else {
                    warning_callback(warnings);
                }                        
            } else {
                if (typeof ok_callback === "function") {
                    ok_callback(image_setting);
                }
            }
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error("get_image_dir error: " + errorThrown);
        }
    });
}

Preview.prototype.update_image_dir = function(
                                        path, 
                                        extension, 
                                        preview_cutoff_min,
                                        preview_cutoff_max,
                                        ok_callback,
                                        error_callback,
                                        warning_callback) {

    console.debug('get_image_dir -> path: ' + path + ', extension: ' + extension);

    $.ajax({
        url: 'filemetaio.py',
        data: { path: path,
                extension: extension,
                output_format: 'json',
                action: 'update_dir',
                flags: 'i',
                preview_cutoff_min: preview_cutoff_min,
                preview_cutoff_max: preview_cutoff_max,
              },
        type: "POST",
        dataType: "json",
        cache: false,
        success: function(jsonRes, textStatus) {
            var i;
            var errors = $(this).renderError(jsonRes);
            var warnings = $(this).renderWarning(jsonRes);
            var image_setting = null;
            for (i = 0; i < jsonRes.length; i++) {
                if (jsonRes[i].object_type == 'image_setting') {
                    image_setting = jsonRes[i];
                }
            }
            if (errors.length > 0) {
                if (typeof error_callback === "function") {
                    console.error(errors);
                } else {
                    error_callback(errors);
                }                
            } else if (warnings.length > 0) {
                if (typeof warning_callback === "function") {
                    console.warn(warnings);
                } else {
                    warning_callback(warnings);
                }                        
            } else {
                if (typeof ok_callback === "function") {
                    ok_callback(image_setting);
                }
            }
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error("getImageDir error: " + errorThrown);
        }
    });
}