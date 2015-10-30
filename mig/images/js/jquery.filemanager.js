/*

  #
  # --- BEGIN_HEADER ---
  #
  # jquery.filemanager - jquery based file manager
  # Copyright (C) 2003-2015  The MiG Project lead by Brian Vinter
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

  # The path normalization code is a modified copy from Node.js and the original
  # Copyright notice follows here:

  Copyright 2009, 2010 Ryan Lienhart Dahl. All rights reserved. Permission
  is hereby granted, free of charge, to any person obtaining a copy of
  this software and associated documentation files (the "Software"), to
  deal in the Software without restriction, including without limitation
  the rights to use, copy, modify, merge, publish, distribute, sublicense,
  and/or sell copies of the Software, and to permit persons to whom the
  Software is furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included
  in all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
  OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
  NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
  LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
  OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
  WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

*/

/* switch on/off console debug globally here */
var enable_debug = false;

/*
   Make sure we can always use console.X without scripts crashing. IE<=9
   does not init it unless in developer mode and things thus randomly fail
   without a trace.
*/
var noOp = function(){}; // no-op function
if (!window.console || !enable_debug) {
    console = {
        debug: noOp,
        log: noOp,
        warn: noOp,
        error: noOp
    }
}
/*
   Make sure we can use Date.now which was not available in IE<9
*/
if (!Date.now) {
    Date.now = function now() {
        return new Date().getTime();
    };
}

if (!enable_debug) {
    console.debug = noOp;
} else {
    console.debug = function(msg){
        console.log(Date.now()+" DEBUG: "+msg);
    };
}

if (jQuery) (function($){

    var pathAttribute = 'rel_path';
    var sorting = [[0, 0]];

    // Use touchscreen interface without need for right clicking
    function touchscreenChecker() {
        var touchscreen = $("#fm_touchscreen[type='checkbox']").is(":checked");
        return touchscreen;
    }

    // Visibility of dot files/dirs
    function showDotfilesChecker() {
        var showDotfiles = $("#fm_dotfiles[type='checkbox']").is(":checked");
        return showDotfiles;
    }

    // refresh table sorting
    function updateSorting() {
        // make sure tablesorter style is applied
        console.debug("force tablesorter update");
        setTimeout(function() {
            $(".fm_files table").trigger("update");
        }, 10);
    }
    // Show/hide dot files/dirs
    function refreshDotfiles() {
        var do_show = showDotfilesChecker();
        $("tr.fm_dotfile, li.fm_dotfile").each(function() {
            var t = $(this);
            setTimeout(function() {
                if (do_show && t.css('display') == 'none') {
                    t.toggle();
                } else if (!do_show && t.css('display') != 'none') {
                    t.toggle();
                }
            }, 10);
        });
        /* seems like a waste but needed to get zebra coloring right */
        updateSorting();
    }

    $.fn.dump = function(element) {
        /* some browsers support toSource as easy dump */
        if (element.toSource != undefined) {
            return element.toSource();
        }
        var a = ["Element dump:"];
        a.push("Raw: " + element);
        for (var k in element) {
            if (element.hasOwnProperty(k)) {
                a.push(k + ": " + element[k]);
            }
        }
        a.push("HTML: " + element.innerHTML);
        return(a.join('\n'));
    }

    $.fn.renderError = function(jsonRes) {

        var errors = '';

        for (var i=0; i<jsonRes.length; i++) {
            if (jsonRes[i]['object_type'] == 'error_text')
                errors +='<span class="errortext error iconspace">'+jsonRes[i].text+'</span><br />';
        }
        return errors;
    }

    $.fn.renderWarning = function(jsonRes) {

        var warnings = '';

        for (var i=0; i<jsonRes.length; i++) {
            if (jsonRes[i]['object_type'] == 'warning')
                warnings +='<span class="warningtext warning iconspace">'+jsonRes[i].text+'</span><br />';
        }
        return warnings;
    }

    $.fn.renderFileoutput = function(jsonRes) {

        var file_output = '';

        for (i = 0; i < jsonRes.length; i++) {
            if (jsonRes[i].object_type=='file_output') {
                for (j = 0; j < jsonRes[i].lines.length; j++) {
                    file_output += jsonRes[i].lines[j];
                }
            }
        }
        return file_output;
    }

    $.fn.tagName = function() {
        return this.get(0).tagName;
    }

    $.fn.parentPath = function(path) {
        // Extract the parent of the path
        if (path.lastIndexOf("/") == (path.length-1)) { // is directory?
            dirPath = path.substring(0, path.length-1);
            dirPath = path.substring(0, dirPath.lastIndexOf('/'))+'/';
        } else {
            dirPath = path.substring(0, path.lastIndexOf('/'))+'/';
        }
        return dirPath;
    }

    $.fn.normalizePath = function(path) {
        /* This is a modified version of the path normalizer from Node.js */
        var parts = path.split("/");
        var keepBlanks = false;
        var directories = [], prev;
        for (var i = 0, l = parts.length - 1; i <= l; i++) {
            var directory = parts[i];

            // if it's blank, but it's not the first thing, and not the last thing, skip it.
            if (directory === "" && i !== 0 && i !== l && !keepBlanks) continue;

            // if it's a dot, and there was some previous dir already, then skip it.
            if (directory === "." && prev !== undefined) continue;

            // if it starts with "", and is a . or .., then skip it.
            if (directories.length === 1 && directories[0] === "" && (
                directory === "." || directory === "..")) continue;

            if (directory === ".." && directories.length && prev !== ".." &&
                prev !== "." && prev !== undefined &&
                (prev !== "" || keepBlanks)) {
                directories.pop();
                prev = directories.slice(-1)[0];
            } else {
                if (prev === ".") directories.pop();
                directories.push(directory);
                prev = directory;
            }
        }
        return directories.join("/");
    }

    $.fn.reload = function reload(path) {
        var reloadPath = path;

        if (reloadPath == '') {
            reloadPath = $(".fm_addressbar input[name='fm_current_path']").val().substr(1);
        }

        // Make sure slash remains for home
        if (reloadPath == '') {
            reloadPath = '/';
        }

        // Trigger the click-event twice for obtaining the original state (collapse+expand).
        /* NOTE: Careful to avoid breakage with paths containing single quote */
        $('.fm_folders [rel_path="'+reloadPath+'"]').click();
        $('.fm_folders [rel_path="'+reloadPath+'"]').click();
    }

    $.fn.targetDir = function(elem) {
        var remote_path = $(elem).attr(pathAttribute);
        /* if called on element without pathAttribute */
        if (remote_path == undefined) {
            remote_path = $(".fm_addressbar input[name='fm_current_path']").val();
        }
        /* fix path anchor */
        if (remote_path == '/') {
            remote_path = './';
        } else {
            remote_path = './'+remote_path;
        }
        return remote_path;
    }

    $.fn.openDir = function(path) {
        /* NOTE: Careful to avoid breakage with paths containing single quote */
        path = path.replace(/%27/g, "'");
        $(".fm_addressbar input[name='fm_current_path']").val(path);
        $.fn.reload(path);
    }

    $.fn.filemanager = function(user_options, clickaction) {

        console.debug("init file manager");

        var clipboard = new Array({'is_dir':false, 'path':''});

        // Note: max-height is broken on autoHeight this is noted as a bug:
        //       http://dev.jqueryui.com/ticket/4820
        //       The stated workaround is used in jsonWrapper.
        var dialogOptions = { width: '800px', autoOpen: false,
                              closeOnEscape: true, modal: true };
        var okDialog = { buttons: {Ok: function()
                                   {$(this).dialog('close');} },
                         width: '800px', autoOpen: false,
                         closeOnEscape: true, modal: true};
        var closeDialog = { buttons: {Close: function()
                                      {$(this).dialog('close');} },
                            width: '800px', autoOpen: false,
                            closeOnEscape: true, modal: true};

        var obj = $(this);
        var statusprogress = $("#fm_statusprogress", obj);
        var statusinfo = $("#fm_statusinfo", obj);

        console.debug("define progress functions");
        function showDirinfo(msg) {
            if (msg == undefined) {
                msg = "";
            }
            console.debug("showDirinfo: "+ msg);
            $(statusinfo).html(msg);
        }
        function startProgress(msg) {
            if (msg == undefined) {
                msg = "working in the background ... please wait";
            }
            var progressLabel = $(".progress-label");
            console.debug("startProgress: "+ msg);
            $(statusprogress).progressbar({
                status: false,
                change: function() {
                    progressLabel.text(msg);
                },
                complete: function() {
                    progressLabel.text("Done!");
                }
            });
            /* now animate */
            $(statusprogress).progressbar("option", "value", false);
            progressLabel.text(msg);
            console.debug("startProgress done");
        }
        function stopProgress(msg) {
            if (msg == undefined) {
                msg = "";
            }
            var progressLabel = $(".progress-label");
            console.debug("stopProgress: "+ msg);
            progressLabel.text(msg);
            $(statusprogress).progressbar("destroy");
            console.debug("stopProgress done");
        }
        console.debug("past progress functions");

        var preview = new Preview(enable_debug);
        function refresh_preview(callback) {
            show_preview(function() {
                preview.refresh(callback);
            });
        }
        function zoom_out_preview(callback) {
            if (preview.settings.zoom > preview.settings.min_zoom) {
                preview.settings.zoom -= 1;
                refresh_preview(callback);
            }
        }
        function zoom_in_preview(callback) {
            if (preview.settings.zoom < preview.settings.max_zoom) {
                preview.settings.zoom += 1;
                refresh_preview(callback);
            }
        }
        function set_visibility_preview_left_tile(visibility) {
            $("#fm_preview_left_tile").css("visibility", visibility);
            $("#fm_preview_left_tile_histogram").css("visibility", visibility);
            $("#fm_preview_left_tile_histogram_actions").css("visibility", visibility);
            $("#fm_preview_left_output").css("visibility", visibility);

        }
        function set_visibility_preview_center_tile(visibility) {
            $("#fm_preview_center_tile").css("visibility", visibility);
        }
        function set_visibility_preview_right_tile(visibility) {
            $("#fm_preview_right_tile").css("visibility", visibility);
            $("#fm_preview_right_output").css("visibility", visibility);
        }
        function show_preview(callback) {
            var center_tile_width_frac = 0.40;
            var files_folders_min_height = 100;
            var previews_height_frac = 0.45;
            var fm_view_padding = 80;
            var left_tile_width;
            var center_tile_width;
            var right_tile_width;
            var folders_height;
            var previews_height;
            var new_content_height;
            var footers_height;
            var new_view_height;
            var fm_previews_width;
            var tiles_width;

            // Calculate and set width settings

            fm_previews_width = $(".fm_previews").width();
            tiles_width = fm_previews_width - $(".fm_preview_menubar").width();

            center_tile_width = Math.round(tiles_width * center_tile_width_frac);
            left_tile_width = (Math.floor((tiles_width - center_tile_width)/2));
            right_tile_width = left_tile_width;

            $(".fm_preview_left_tile").css("width", left_tile_width + "px");
            $(".fm_preview_center_tile").css("width", center_tile_width + "px");
            $(".fm_preview_right_tile").css("width", right_tile_width + "px");

            // Calculate and set height settings

            footers_height = $("body").height() - $(".contentblock").height();
            new_content_height = $(window).height() - footers_height;
            new_view_height = new_content_height - $(".fm_statusbar").height() - $(".fm_path_breadcrumbs").height() - fm_view_padding;

            if (preview.settings.zoom == 0) {
                previews_height = 0;
                files_folders_height = new_view_height;
            }
            else if (preview.settings.zoom == 1) {
                previews_height = Math.round(previews_height_frac * new_view_height);
                files_folders_height = new_view_height - previews_height;
                files_folders_height = files_folders_height < files_folders_min_height ?
                    files_folders_min_height : files_folders_height
            }
            else if (preview.settings.zoom > 1) {
                previews_height = new_view_height;
                files_folders_height = 0;
            }

            preview.settings.height = previews_height;

            $(".contentblock").animate({height: new_content_height + 'px'},
                                       {duration: options.collapseSpeed,
                                        easing: options.collapseEasing});

            $(".fm_previews").animate({height: preview.settings.height + 'px'},
                                      {duration: options.collapseSpeed,
                                       easing: options.collapseEasing,
                                       complete:
                                       function() {
                                           $(".fm_folders").animate({height: files_folders_height + 'px'},
                                                                    {duration: options.collapseSpeed,
                                                                     easing: options.collapseEasing});
                                           $(".fm_files").animate({height: files_folders_height + 'px'},
                                                                  {duration: options.collapseSpeed,
                                                                   easing: options.collapseEasing});
                                           if (preview.settings.zoom == 0) {
                                               $("#fm_preview_menubar").css('visibility', 'hidden');
                                               set_visibility_preview_left_tile('hidden');
                                               set_visibility_preview_center_tile('hidden');
                                               set_visibility_preview_right_tile('hidden');

                                           }
                                           else {
                                               $("#fm_preview_menubar").css('visibility', 'visible');
                                               set_visibility_preview_left_tile('visible');
                                               set_visibility_preview_center_tile('visible');
                                               set_visibility_preview_right_tile('visible');
                                           }
                                           if (typeof callback === "function") {
                                               callback();
                                           }
                                       }});
        }

        function clickEvent(el) {

            if (!options['imagesettings']) {
                console.debug('clickEvent: imagesettings is false');
            } else {

                // Grey out cutoff butten as default

                $("#preview_histogram_set_cutoff_button").attr('disabled', true);

                // Get image data

                $.ajax({url: 'filemetaio.py',
                        data: { path: $(el).attr(pathAttribute), output_format: 'json' ,
                                action: 'get_file', flags: 'i'},
                        type: "GET",
                        dataType: "json",
                        cache: false,
                        success: function(jsonRes, textStatus) {
                            var errors = $(this).renderError(jsonRes);
                            var warnings = $(this).renderWarning(jsonRes);
                            var right_html_out = '';
                            var left_html_out = '';
                            var image_filepath;
                            for (i = 0; i < jsonRes.length; i++) {
                                if (jsonRes[i].object_type == 'image_meta') {
                                    $(".fm_previews input[name=fm_preview_base_path]").val(jsonRes[i].base_path);
                                    $(".fm_previews input[name=fm_preview_path]").val(jsonRes[i].path);
                                    $(".fm_previews input[name=fm_preview_filename]").val(jsonRes[i].name);
                                    $(".fm_previews input[name=fm_preview_extension]").val(jsonRes[i].extension);

                                    preview_image_url = jsonRes[i].preview_image_url;
                                    preview_histogram = new Uint32Array(jsonRes[i].preview_histogram);

                                    if (jsonRes[i].path === '') {
                                        image_filepath = jsonRes[i].base_path + '/' + jsonRes[i].name;
                                    }
                                    else {
                                        image_filepath = jsonRes[i].base_path + '/' + jsonRes[i].path +  "/" + jsonRes[i].name;
                                    }
                                    right_html_out  += '<p>Image: ' + image_filepath + '</p>'
                                        + '<p>Image Type: ' + jsonRes[i].image_type + '</p>'
                                        + '<p>Data Type: ' + jsonRes[i].data_type + '</p>'
                                        + '<p>Offset: ' + jsonRes[i].offset + '</p>'
                                        + '<p>X dimension: ' + jsonRes[i].x_dimension + '</p>'
                                        + '<p>Y dimension: ' + jsonRes[i].y_dimension + '</p>'
                                        + '<p>Min Value: ' + Number(jsonRes[i].min_value).toExponential(preview.get_format_decimals()) + '</p>'
                                        + '<p>Max Value: ' + Number(jsonRes[i].max_value).toExponential(preview.get_format_decimals()) + '</p>'
                                        + '<p>Mean Value: '  + Number(jsonRes[i].mean_value).toExponential(preview.get_format_decimals()) + '</p>'
                                        + '<p>Median Value: ' + Number(jsonRes[i].median_value).toExponential(preview.get_format_decimals()) + '</p>';

                                    // TODO: Move input fields HTML to fileman.py ?

                                    left_html_out += '<input type="hidden" value="' + jsonRes[i].preview_cutoff_min + '" name="min_value" />' +
                                        '<p><span id="fm_preview_left_output_min_value_show"></span></p>' +
                                        '<input type="hidden" value="' + jsonRes[i].preview_cutoff_max + '" name="max_value" />' +
                                        '<p><span id="fm_preview_left_output_max_value_show"></span></p>' +
                                        '<input type="hidden" value="' + jsonRes[i].preview_image_scale + '" name="scale_value" />' +
                                        '<p><span id="fm_preview_left_output_preview_image_scale_value_show"></span></p>'

                                    // Check for preview settings status, and mark cutoff butten active if folder ready

                                    $.ajax({url: 'filemetaio.py',
                                            data: { path: jsonRes[i].base_path,
                                                    extension: jsonRes[i].extension,
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
                                                if (errors.length > 0) {
                                                    console.debug(errors);
                                                } else if (warnings.length > 0) {
                                                    console.debug(warnings);
                                                }
                                                for (i = 0; i < jsonRes.length; i++) {
                                                    if (jsonRes[i].object_type == 'image_setting') {
                                                        if (jsonRes[i].settings_status.toLowerCase() == 'ready' ) {
                                                            $("#preview_histogram_set_cutoff_button").attr('disabled', false);
                                                        }
                                                    }
                                                }
                                            }
                                           });
                                }
                            }
                            if (errors.length > 0) {
                                $("#fm_preview_right_output").html(errors);
                                $("#fm_preview_left_output").html('');
                                console.debug(errors);
                            } else if (warnings.length > 0) {
                                $("#fm_preview_right_output").html(warnings);
                                $("#fm_preview_left_output").html('');
                                console.debug(warnings);
                            } else {
                                $("#fm_preview_right_output").html(right_html_out);
                                $("#fm_preview_left_output").html(left_html_out);

                                preview.set_histogram_data(preview_histogram);
                                preview.settings.zoom = 1;
                                show_preview(function() {
                                    preview.load(preview_image_url);
                                });
                            }
                        }
                       });
            }
        }

        function doubleClickEvent(el) {
            if (clickaction != undefined) {
                clickaction(el);
                return;
            }
            // if no clickaction is provided, default to opening and showing
            if ($(el).hasClass('directory')) {
                /* NOTE: careful to avoid breakage with single quote in paths */
                $('.fm_folders [rel_path="'+$(el).attr(pathAttribute)+'"]').click();
            } else {
                // Do stuff with files.
                callbacks['show']('action', el, null);
            }
        }

        function toTimestamp(strDate){
            var datum = Date.parse(strDate);
            return datum/1000;
        }

        function copy(src, dst) {

            var flag = '';

            // Handle directory copy, set flag and alter destination path.
            if (clipboard['is_dir']) {

                flag = 'r';
                // Extract last directory from source
                dst += src.split('/')[src.split('/').length-2];
            }
            if (dst == '') {
                dst = '.';
            }

            $("#cmd_dialog").dialog(okDialog);
            $("#cmd_dialog").dialog('open');
            $("#cmd_dialog").html('<p class="spinner iconspace">Copying... "'+src+'" <br />To: "'+dst+'"</p>');

            $.post('cp.py', { src: src,
                              dst: dst,
                              output_format: 'json',
                              flags: flag
                            },
                   function(jsonRes, textStatus) {
                       stopProgress();
                       var errors = $(this).renderError(jsonRes);
                       var warnings = $(this).renderWarning(jsonRes);
                       if (errors.length > 0) {
                           $($("#cmd_dialog").html('<p>Error:</p>'+errors));
                       } else if (warnings.length > 0) {
                           $($("#cmd_dialog").html('<p>Warning:</p>'+warnings));
                       } else {
                           // Only reload if destination is current folder
                           if ($(".fm_addressbar input[name='fm_current_path']").val().substr(1) == dst.substring(0, dst.lastIndexOf('/'))+'/') {
                               $(".fm_files").parent().reload($(".fm_addressbar input[name='fm_current_path']").val().substr(1));
                           }
                           $("#cmd_dialog").dialog('close');
                       }
                   }, "json"
                  );

        }

        function parseWrapped(jsonRes, jsonSettings) {
            var misc_output = '';
            var j, field;
            for (var i = 0; i < jsonRes.length; i++) {
                if (jsonRes[i]['object_type'] == 'submitstatuslist') {
                    field = 'submitstatuslist';
                    for (j = 0; j < jsonRes[i][field].length; j++) {
                        if (jsonRes[i][field][j]['status']) {
                            misc_output += '<p class="info iconspace">Submitted "'
                                + jsonRes[i][field][j]['name']
                                + '"</p><p>Job identfier: "'
                                +jsonRes[i][field][j]['job_id']
                                + '"</p>';
                        } else {
                            misc_output +=  '<p class="errortext error iconspace">Failed submitting:</p><p>'
                                + jsonRes[i][field][j]['name']
                                + ' '+jsonRes[i][field][j]['message']
                                + '</p>';
                        }
                    }
                } else if (jsonRes[i]['object_type'] == 'stats') {
                    field = 'stats';
                    for (j = 0; j < jsonRes[i][field].length; j++) {
                        misc_output += '<h4>Stat on ' + jsonSettings['path'] + '</h4>'
                            + '<p>mode: ' + jsonRes[i][field][j]['mode']
                            + '</p><p>size: ' + jsonRes[i][field][j]['size']
                            + '</p><p>atime: ' + parseInt(jsonRes[i][field][j]['atime'])
                            + '</p><p>mtime: ' + parseInt(jsonRes[i][field][j]['mtime'])
                            + '</p><p>ctime: ' + parseInt(jsonRes[i][field][j]['ctime'])
                            + '</p>';
                    }
                } else if (jsonRes[i]['object_type'] == 'filewcs') {
                    field = 'filewcs';
                    for (j = 0; j < jsonRes[i][field].length; j++) {
                        misc_output += '<h4>Word count on ' + jsonRes[i][field]['name'] + '</h4>'
                            + '<p>lines: ' + jsonRes[i][field][j]['lines']
                            + '</p><p>words: ' + jsonRes[i][field][j]['words']
                            + '</p><p>bytes: ' + jsonRes[i][field][j]['bytes']
                            + '</p>';
                    }
                }
            }
            return misc_output;
        }

        function jsonWrapper(el, dialog, url, jsonOptions) {

            var jsonSettings = {path: $(el).attr(pathAttribute),
                                output_format: 'json'};
            var lastinfo = $(statusinfo).html();

            $.fn.extend(jsonSettings, jsonOptions);

            startProgress();

            /* We used to use $.getJSON() here but now some back ends require POST */
            $.post(url, jsonSettings,
                   function(jsonRes, textStatus) {

                       var errors = $(this).renderError(jsonRes);
                       var warnings = $(this).renderWarning(jsonRes);
                       var file_output = $(this).renderFileoutput(jsonRes);
                       var misc_output = parseWrapped(jsonRes, jsonSettings);

                       stopProgress(lastinfo);
                       if ((errors.length > 0)
                           || (warnings.length > 0)
                           || (file_output.length > 0)
                           || (misc_output.length > 0)) {

                           $(dialog).dialog(okDialog);
                           $(dialog).dialog('open');

                           if (file_output.length > 0) {
                               file_output = '<pre>'+file_output+'</pre>';
                           }

                           $(dialog).html(errors+warnings+file_output+misc_output);
                       }

                       /* Always refresh to show any partial results upon error */
                       $(".fm_files").parent().reload($(this).parentPath($(el).attr(pathAttribute)));
                   }, "json"
                  );
        }

        // Callback helpers for context menu
        var callbacks = {

            open:   function (action, el, pos) {
                $(".fm_files").parent().reload($(el).attr(pathAttribute));
            },
            show:   function (action, el, pos) {
                //console.debug("show "+action+" "+el+" "+pos);
                var path_enc = encodeURI($(el).attr(pathAttribute));
                window.open('/cert_redirect/'+path_enc);
            },
            download:   function (action, el, pos) {
                /*
                  Use 'cat' to stream small files but raw request for big
                  files to avoid hogging memory. Take action based on file
                  size in bytes.
                */
                var file_size = $("div.bytes", el).text();
                var max_stream_size = 64*1024*1024;
                if (file_size > max_stream_size) {
                    var path_enc = encodeURI($(el).attr(pathAttribute));
                    window.open('/cert_redirect/'+path_enc);
                } else {
                    /* Path may contain URL-unfriendly characters */
                    document.location = 'cat.py?path='
                        +encodeURIComponent($(el).attr(pathAttribute))+'&output_format=file';
                }
            },
            edit:   function (action, el, pos) {
                $("#editor_dialog textarea[name='editarea']").val('');
                $("#editor_output").removeClass()
                $("#editor_output").addClass("hidden");
                $("#editor_output").html('');
                $("#editor_dialog").dialog({
                    buttons: {
                        'Save Changes': function() {
                            startProgress("Saving file...");
                            $("#editor_dialog div.spinner").html("Saving file...").show();
                            $("#editor_form").submit();
                        },
                        'Close': function() {
                            $(this).dialog('close');
                        },
                        'Download': function() {
                            /* Path may contain URL-unfriendly characters */
                            document.location = 'cat.py?path='
                                +encodeURIComponent($(el).attr(pathAttribute))
                                +'&output_format=file';
                        }
                    },
                    autoOpen: false, closeOnEscape: true,
                    modal: true, width: '800px'
                });
                $("#editor_dialog div.spinner").html("Loading file...").show();
                $("#editor_dialog input[name='submitjob']").attr('checked', false);
                $("#editor_dialog input[name='path']").val('./'+$(el).attr(pathAttribute));
                $("#editor_dialog").dialog('open');

                // Grab file info
                $.ajax({
                    url: 'cat.py',
                    data: { path: $(el).attr(pathAttribute), output_format: 'json' },
                    type: "GET",
                    dataType: "json",
                    cache: false,
                    success: function(jsonRes, textStatus) {
                        var file_output = '';
                        for (i = 0; i < jsonRes.length; i++) {
                            if (jsonRes[i].object_type=='file_output') {
                                for (j = 0; j < jsonRes[i].lines.length; j++) {
                                    file_output += jsonRes[i].lines[j];
                                }
                            }
                        }
                        // Force refresh on editor field truncating any unsaved contents
                        disable_editorarea_editor(lastEdit);
                        $("#editor_dialog textarea[name='editarea']").val(file_output);
                        $("#editor_dialog div.spinner").html("").hide();
                        var activeEntry = $("#switcher .currentSet");
                        // activeEntry has currentSet and type class - extract type
                        activeEntry.removeClass("currentSet");
                        var activeSet = activeEntry.attr("class");
                        activeEntry.addClass("currentSet");
                        enable_editorarea_editor(activeSet)
                    }
                });

            },
            create:    function (action, el, pos) {
                $("#editor_output").removeClass()
                $("#editor_output").html('');
                $("#editor_dialog").dialog({
                    buttons: {
                        'Save Changes': function() {
                            startProgress("Saving file ...");
                            $("#editor_dialog div.spinner").html("Saving file...").show();
                            $("#editor_form").submit();
                        },
                        'Close': function() {
                            $(this).dialog('close');
                        }
                    },
                    autoOpen: false, closeOnEscape: true,
                    modal: true, width: '800px'
                });

                // determine file-name of new file with fallback to default in
                // current dir if dir is empty
                var new_file_name = $(".fm_addressbar input[name='fm_current_path']").val()+'new_empty_file-1';
                var name_taken = true;

                for (var i=1; name_taken; i++) {
                    name_taken = false;
                    $("#fm_filelisting tbody tr").each(function(item) {
                        if ($(this).attr('rel_path') == $(el).attr(pathAttribute)+'new_empty_file'+'-'+i) {
                            name_taken = true;
                        } else {
                            new_file_name = $(el).attr(pathAttribute)+'new_empty_file'+'-'+i;
                        }
                    });

                }

                $("#editor_dialog input[name='submitjob']").attr('checked', false);
                $("#editor_dialog input[name='path']").val('./'+new_file_name);
                $("#editor_dialog textarea[name='editarea']").val('');
                $("#editor_dialog div.spinner").html("").hide();
                $("#editor_dialog").dialog('open');

            },
            cat:    function (action, el, pos) {
                jsonWrapper(el, '#cmd_dialog', 'cat.py'); },
            head:   function (action, el, pos) {
                jsonWrapper(el, '#cmd_dialog', 'head.py'); },
            tail:   function (action, el, pos) {
                jsonWrapper(el, '#cmd_dialog', 'tail.py'); },
            wc:   function (action, el, pos) {
                jsonWrapper(el, '#cmd_dialog', 'wc.py'); },
            touch:   function (action, el, pos) {
                jsonWrapper(el, '#cmd_dialog', 'touch.py'); },
            stat:   function (action, el, pos) {
                jsonWrapper(el, '#cmd_dialog', 'statpath.py'); },
            truncate:   function (action, el, pos) {
                var truncate_path = $(el).attr(pathAttribute);
                var truncate_size = 0;
                /* TODO: add support for a truncate size field? */
                $("#cmd_dialog").html('<p><span class="ui-icon ui-icon-alert" style="float:left; margin:0 7px 20px 0;"></span>The contents of "'+truncate_path+'" will be permanently erased. Are you sure?</p></div>');
                $("#cmd_dialog").dialog({
                    buttons: {
                        Ok: function() {
                            var truncate_size = $("#truncate_form input[name='size']").val();
                            $(this).dialog('close');
                            jsonWrapper(el, '#cmd_dialog', 'truncate.py',
                                        {path: $(el).attr(pathAttribute),
                                         size: truncate_size});
                        },
                        Cancel: function() {
                            $(this).dialog('close');
                        }
                    },
                    width: '800px', autoOpen: false,
                    closeOnEscape: true, modal: true
                });
                $("#cmd_dialog").dialog('open');
            },
            spell:   function (action, el, pos) {
                jsonWrapper(el, '#cmd_dialog', 'spell.py'); },
            md5sum:   function (action, el, pos) {
                jsonWrapper(el, '#cmd_dialog', 'chksum.py', {path: $(el).attr(pathAttribute), hash_algo: "md5"}); },
            sha1sum:   function (action, el, pos) {
                jsonWrapper(el, '#cmd_dialog', 'chksum.py', {path: $(el).attr(pathAttribute), hash_algo: "sha1"}); },
            pack:    function (action, el, pos) {
                /* pack file or directory to user specified file */
                var current_dir = '';
                var target = $(el).attr(pathAttribute);
                var path_name = '';
                pathEl = target.split('/');
                if (target.lastIndexOf("/") == (target.length-1)) {
                    path_name = pathEl[pathEl.length-2];
                    target = target.substring(0, target.lastIndexOf('/'));
                } else {
                    path_name = pathEl[pathEl.length-1];
                }
                current_dir = target.substring(0, target.lastIndexOf('/'));

                // Initialize the form with default to zip file
                $("#pack_form input[name='current_dir']").val(current_dir);
                $("#pack_form input[name='src']").val(path_name);
                $("#pack_form input[name='dst']").val(path_name + '.zip');
                $("#pack_output").html('');
                $("#pack_dialog").dialog({
                    buttons: {
                        Ok: function() {
                            startProgress("Packing folder...");
                            $("#pack_form").submit();
                        },
                        Cancel: function() {
                            $(this).dialog('close');
                        }
                    },
                    autoOpen: false, closeOnEscape: true,
                    modal: true, width: '500px'
                });
                $("#pack_dialog").dialog('open');
            },
            unpack:   function (action, el, pos) {
                var dst = $(".fm_addressbar input[name='fm_current_path']").val();
                // unpack uses src instead of path parameter
                console.debug("starting unpack");
                jsonWrapper(el, '#cmd_dialog', 'unpack.py', {dst: dst, src: $(el).attr(pathAttribute), path: ''});
                console.debug("done in unpack");
            },
            submit: function (action, el, pos) {
                jsonWrapper(el, '#cmd_dialog', 'submit.py');
            },
            copy:   function (action, el, pos) {
                clipboard['is_dir'] = $(el).hasClass('directory');
                clipboard['path'] = $(el).attr(pathAttribute);
                console.debug('copy '+clipboard['path']+":"+clipboard['is_dir']);
            },
            paste:  function (action, el, pos) {
                var target_path = $(el).attr(pathAttribute);
                if (!clipboard['path']) {
                    console.error("nothing previously copied - nothing to paste");
                    return;
                }
                if (target_path == undefined) {
                    target_path = $.fn.targetDir();
                    console.warning("paste falling back to dst "+target_path);
                }
                console.debug('copy '+clipboard['path']+":"+target_path);
                startProgress("Copying...");
                copy(clipboard['path'], target_path);
            },
            rm:     function (action, el, pos) {
                var flags = '';
                var rm_path = $(el).attr(pathAttribute);
                if ($(el).attr(pathAttribute).lastIndexOf('/') == $(el).attr(pathAttribute).length-1) {
                    flags = 'r';
                }
                $("#cmd_dialog").html('<p><span class="ui-icon ui-icon-alert" style="float:left; margin:0 7px 20px 0;"></span>"'+rm_path+'" will be permanently deleted. Are you sure?</p></div>');
                $("#cmd_dialog").dialog({
                    buttons: {
                        Ok: function() {
                            $(this).dialog('close');
                            jsonWrapper(el, '#cmd_dialog', 'rm.py', {flags: flags});
                        },
                        Cancel: function() {
                            $(this).dialog('close');
                        }
                    },
                    width: '800px', autoOpen: false,
                    closeOnEscape: true, modal: true
                });
                $("#cmd_dialog").dialog('open');
            },
            upload: function (action, el, pos) {
                var open_dialog = mig_fancyuploadchunked_init("upload_dialog");
                var remote_path = $.fn.targetDir(el);
                $("#upload_form input[name='remotefilename_0']").val(remote_path);
                $("#upload_form input[name='fileupload_0_0_0']").val('');
                $("#upload_output").html('');
                open_dialog("Upload Files",
                            function () {
                                $(".fm_files").parent().reload('');
                            }, remote_path, false);
            },
            mkdir:  function (action, el, pos) {
                // Initialize the form
                $("#mkdir_form input[name='current_dir']").val($(el).attr(pathAttribute));
                $("#mkdir_form input[name='path']").val('');
                $("#mkdir_output").html('');
                $("#mkdir_dialog").dialog({
                    buttons: {
                        Ok: function() {
                            startProgress("Creating folder...");
                            $("#mkdir_form").submit();
                            $(".fm_files").parent().reload('');
                        },
                        Cancel: function() {
                            $(this).dialog('close');
                        }
                    },
                    autoOpen: false, closeOnEscape: true,
                    modal: true
                });
                $("#mkdir_dialog").dialog('open');
            },

            // NOTE: it seems that the mv.py backend does not allow
            //       for folders to be moved so only renaming of files works.
            rename: function(action, el, pos) {
                var path_name = '';
                pathEl = $(el).attr(pathAttribute).split('/');
                if ($(el).attr(pathAttribute).lastIndexOf('/') == $(el).attr(pathAttribute).length-1) {
                    path_name = pathEl[pathEl.length-2];
                } else {
                    path_name = pathEl[pathEl.length-1];
                }

                // Initialize the form
                $("#rename_form input[name='src']").val($(el).attr(pathAttribute));
                $("#rename_form input[name='name']").val(path_name);
                $("#rename_output").html('');
                $("#rename_dialog").dialog({
                    buttons: {
                        Ok: function() {
                            startProgress("Renaming...");
                            $("#rename_form").submit();
                            $(".fm_files").parent().reload('');
                        },
                        Cancel: function() {
                            $(this).dialog('close');
                        }
                    },
                    autoOpen: false, closeOnEscape: true,
                    modal: true
                });
                $("#rename_dialog").dialog('open');
            },
            grep:  function (action, el, pos) {
                // Initialize the form
                $("#grep_form input[name='path']").val($(el).attr(pathAttribute));
                $("#grep_form input[name='pattern']").val('');
                $("#grep_dialog").dialog({
                    buttons: {
                        Ok: function() {
                            startProgress("Searching for text...");
                            /* user may specify path pattern so don't use implict elem path */
                            var path = $("#grep_form input[name='path']").val();
                            var pattern = $("#grep_form input[name='pattern']").val();
                            $(this).dialog('close');
                            jsonWrapper(el, '#cmd_dialog', 'grep.py', {path: path, pattern: pattern});
                        },
                        Cancel: function() {
                            $(this).dialog('close');
                        }
                    },
                    autoOpen: false, closeOnEscape: true,
                    modal: true
                });
                $("#grep_dialog").dialog('open');
                $("#grep_form input[name='pattern']").focus();
            },
            imagesettings: function(action, el, pos) {
                var rel_path = $(el).attr(pathAttribute);
                var open_dialog = mig_imagesettings_init("imagesettings_dialog", rel_path, options);
                open_dialog("Image Settings");
            }

        };

        var defaults = {
            root: '/',
            connector: 'somewhere.py',
            param: 'path',
            folderEvent: 'click',
            expandSpeed: 100,
            collapseSpeed: 100,
            expandEasing: null,
            collapseEasing: null,
            multiFolder: true,
            loadMessage: 'Loading...',
            actions: callbacks,
            subPath: '/',
            dragndrop: true,
            filespacer: true,
            enableSubmit: true,
            selectOnly: false,
            imagesettings: false
        };

        var options = $.extend(defaults, user_options);

        // reestablish defaults for undefined actions:
        $.each(callbacks, function(name, fct) {
            if (options['actions'][name] == undefined) {
                options['actions'][name] = callbacks[name];
            } else {
                //console.log(name + " overloaded");
            }
        });

        return this.each(function() {
            obj = $(this);

            // Create the tree structure on the left and populate the table
            // list of files on the right
            function showBranch(folder_pane, t) {

                console.debug('in showBranch '+t);
                var file_pane = $(".fm_files", obj);
                var files_table = $(".fm_files table tbody");
                var statusinfo = $("#fm_statusinfo", obj);
                var statusprogress = $("#fm_statusprogress", obj);
                var path_breadcrumbs = $("#fm_xbreadcrumbs", obj);
                var addressbar = $(".fm_addressbar", obj);
                var timestamp = 0;
                var emptyDir = true;
                var bc_html = '';
                var entry_html = '';
                var onclick_action = '';
                var subdir_path = t;
                var subdir_path_esc;
                var subdir_name = '';
                var a_class = '';
                var li_class = 'class="current"';
                var found_root = false;

                // append current subdir parts to breadcrumbs (from right to left)
                while (!found_root) {
                    if (subdir_path == '/') {
                        a_class = 'class="home"';
                        subdir_name = '/';
                        found_root = true;
                    } else {
                        // remove trailing slash
                        subdir_name = subdir_path.substring(0, subdir_path.length-1);
                        subdir_name = subdir_name.substring(subdir_name.lastIndexOf('/')+1, subdir_name.length);
                    }
                    /* NOTE: Careful to avoid breakage with paths containing single quote */
                    subdir_path_esc = subdir_path.replace(/'/g, "%27");
                    onclick_action = "$.fn.openDir('"+subdir_path_esc+"'); return false;";
                    entry_html = '  <li '+li_class+'>';
                    /* Path may contain URL-unfriendly characters */
                    entry_html += '    <a href="?path='+encodeURIComponent(subdir_path)+'" '+a_class;
                    entry_html += ' onclick="'+onclick_action+'">'+subdir_name+'</a>';
                    entry_html += '    <ul>';
                    entry_html += '    </ul>';
                    entry_html += '  </li>';
                    bc_html = entry_html + '\n' + bc_html;
                    subdir_path = $.fn.parentPath(subdir_path);
                    // remove current class after first
                    li_class = '';
                }

                path_breadcrumbs.html(bc_html);
                // Must reinit every time to make collapsible work
                $("#fm_xbreadcrumbs").xBreadcrumbs({ collapsible: true,
                                                     collapsedWidth: 28 });

                // Refix the root

                console.debug('refix root '+t);

                showDirinfo();
                startProgress('Loading directory entries...');
                console.debug('refresh directory entries '+t);
                $.ajax({
                    url: options.connector,
                    type: "GET",
                    dataType: "json",
                    data: { path: t, output_format: 'json', flags: 'fa' },
                    cache: false,
                    success: function(jsonRes, textStatus) {
                        console.debug('begin ajax handler '+t);

                        // Place ls.py output in listing array
                        var cur_folder_names = new Array();
                        var cur_file_names = new Array();
                        var listing = new Array();
                        var i, j;
                        for (i = 0; i < jsonRes.length; i++) {
                            if (jsonRes[i].object_type == 'dir_listings') {
                                for (j = 0; j < jsonRes[i].dir_listings.length; j++) {
                                    listing = listing.concat(jsonRes[i].dir_listings[j].entries);
                                }
                            }
                        }

                        stopProgress();
                        startProgress('Updating directory entries...');

                        var folders = '';

                        // Root node if not already created
                        if (t == '/' && $(".fm_folders li.userhome").length == 0) {
                            folders += '<ul class="jqueryFileTree"><li class="directory expanded userhome" rel_path="/" title="Home"><div>/</div>\n';
                        }

                        // Regular nodes from here on after
                        folders += '<ul class="jqueryFileTree">\n';

                        var total_file_size = 0;
                        var file_count = 0.0;
                        var chunk_files = 500;
                        var is_dir = false;
                        var base_css_style = 'file';
                        var icon = '';
                        var dotfile = '';
                        var entry_title = '';
                        var entry_menu = '';
                        var entry_html = '', entries_html = '';

                        var dir_prefix = '';
                        var path = '';

                        $(files_table).empty();
                        $(".jqueryFileTree.start").remove();
                        for (i = 0; i < listing.length; i++) {

                            // ignore the pseudo-dirs
                            if ((listing[i]['name'] == '.') ||
                                (listing[i]['name'] == '..')) {
                                continue;
                            }

                            is_dir = listing[i]['type'] == 'directory';
                            base_css_style = 'file';
                            icon = '';
                            dotfile = '';
                            dir_prefix = '__';

                            // Stats for the statusbar
                            file_count++;
                            total_file_size += listing[i]['file_info']['size'];

                            path = listing[i]['name'];
                            if (t != '/') { // Do not prepend the fake-root.
                                path = t+path;
                            }
                            if (listing[i]['name'].charAt(0) == '.') {
                                dotfile = 'fm_dotfile'
                            }

                            entry_title = path + ' ' + listing[i]['special'];
                            entry_menu = 'box ';
                            if (is_dir) {
                                entry_menu += 'menu-1';
                                base_css_style = 'directory';
                                icon = 'directoryicon ' + listing[i]['extra_class'];

                                path += '/';
                                folders +=  '<li class="' + entry_menu + ' ' + icon + ' ' + dotfile +
                                    ' ' + base_css_style + ' collapsed" rel_path="' + path +
                                    '" title="' + entry_title + '"><div>' +
                                    listing[i]['name'] + '</div></li>\n';
                                dir_prefix = '##';

                                cur_folder_names.push(listing[i]['name']);

                            } else {
                                entry_menu += 'menu-1';
                                icon = 'fileicon';
                                cur_file_names.push(listing[i]['name']);
                            }

                            /* Optimize rendering of intermediate dirs */
                            if (options.subPath) {
                                console.log("skip subpath rendering for "+path);
                                continue;
                            }

                            /* manually build entry to reduce risk of script timeout warnings
                               from excessive html DOM manipulation.
                               Finally append it all in one go to save a lot of overhead.
                            */
                            entry_html = '<tr class="' + entry_menu + ' ' + base_css_style + ' ' + dotfile +
                                '" title="' + entry_title + '" rel_path="' + path + '">' +
                                '<td style="padding-left: 20px;" class="'+ entry_menu + ' ' + icon + ' ext_' +
                                listing[i]['file_info']['ext'].toLowerCase() + '"><div>' + dir_prefix +
                                listing[i]['name'] + '</div>' + listing[i]['name'] +
                                '</td><td><div class="bytes">' + listing[i]['file_info']['size'] +
                                '</div>' + pp_bytes(listing[i]['file_info']['size']) +
                                '</td><td><div>' + listing[i]['file_info']['ext'] +
                                '</div>' + listing[i]['file_info']['ext'] +
                                '</td><td><div>' + listing[i]['file_info']['created'] + '</div>' +
                                pp_date(listing[i]['file_info']['created']) + '</td></tr>';
                            entries_html += entry_html;
                            emptyDir = false;

                            /* chunked updates - append after after every chunk_files entries */
                            if (file_count % chunk_files == 0) {
                                console.debug('append chunk of ' + chunk_files + ' files in '+t);
                                $(files_table).append(entries_html);
                                entries_html = '';
                            }
                        }

                        /* Optimize rendering of intermediate dirs */
                        if (!options.subPath && file_count % chunk_files != 0) {
                            console.debug('append remaining ' + file_count % chunk_files + ' files in '+t);
                            $(files_table).append(entries_html);
                        }

                        folders += '</ul>\n';

                        // End the root node
                        if (t == '/') {
                            folders += '</li></ul>\n';
                        }

                        console.debug('update status bar');

                        // Prefix '/' for the visual presentation of the current path.
                        if (t.substr(0, 1) == '/') {
                            addressbar.find("input[name='fm_current_path']").val(t);
                        } else {
                            addressbar.find("input[name='fm_current_path']").val('/'+t);
                        }

                        // Update statusbar
                        showDirinfo(file_count+' files in current folder of total '+pp_bytes(total_file_size)+' in size.');
                        stopProgress();

                        console.debug('append folder html entries');
                        folder_pane.append(folders);
                        folder_pane.removeClass('wait').removeClass("leftpad");

                        console.debug('show active folder');
                        if (options.root == t) {
                            console.debug('show root');
                            folder_pane.find('UL:hidden').show();
                        } else {
                            console.debug('locate other folder: '+t);
                            //folder_pane.find('UL:hidden').slideDown(
                            /* NOTE: this find is quite expensive for some reason (seconds!)
                               and does not appear to do anything useful.
                               Replaced with cheaper static select.
                            */
                            //var folder_elem = folder_pane.find('UL:hidden');
                            //var folder_elem = folder_pane.children()[1];
                            var folder_elem = $(".fm_folders li.expanded").last();

                            /* Scroll to element in folder pane */
                            //console.debug('scroll to folder '+$.fn.dump($(folder_elem)));
                            /* scroll to active folder - slightly cumbersome calculation */
                            var scrollPos = $(folder_elem).offset().top -
                                $(".fm_folders").offset().top +
                                $(".fm_folders").scrollTop() -
                                $(".fm_folders").height()/2;
                            $(".fm_folders").animate({
                                scrollTop: scrollPos
                            }, options.expandSpeed);
                            //$(".fm_folders").scrollTop(scrollPos);
                            /*
                              console.debug('slide down to open folder'+$.fn.dump($(folder_elem)));
                              $(folder_elem).slideDown(
                              { duration: options.expandSpeed,
                              easing: options.expandEasing });
                            */
                            //console.debug('scrolled to folder pos');
                        }

                        /* UI stuff: contextmenu, drag'n'drop. */
                        console.debug('set up UI');

                        // Always preserve a small space for pasting into the folder, quick-uploading, etc
                        var headerHeight = 20;
                        var spacerHeight = 40;
                        var uploaderHeight = 40;
                        var extraHeight = spacerHeight + uploaderHeight;
                        if ($("#fm_filelisting").height() + extraHeight < $(".fm_files").height() - headerHeight) {
                            extraHeight = $(".fm_files").height() - $("#fm_filelisting").height() - headerHeight;
                        }

                        if (options.filespacer) {
                            if (!options.uploadspace)
                                spacerHeight = extraHeight;
                            else
                                spacerHeight = extraHeight/2;
                            var rel_path = "";
                            /* add or update existing filespacer */
                            if ($(".fm_files div.filespacer").length == 0) {
                                //console.debug("add filespacer");
                                $(".fm_files").append('<div class="filespacer" style="height: '+spacerHeight+'px ;" rel_path="" title=""+></div>');
                            }

                            if (t != '/') { // Do not prepend the fake-root.
                                rel_path = t;
                            }
                            //console.debug("update filespacer with path: "+rel_path);
                            $(".fm_files div.filespacer").css("height", spacerHeight+"px")
                                .attr("rel_path", rel_path)
                                .attr("title", rel_path);
                        }
                        if (options.uploadspace) {
                            if (!options.filespacer)
                                uploaderHeight = extraHeight;
                            else
                                uploaderHeight = extraHeight/2;
                            var rel_path = "";
                            /* add or update existing uploadspace */
                            if ($(".fm_files div.uploadspace").length == 0) {
                                //console.debug("add uploadspace");
                                $(".fm_files").append('<div class="uploadspace centertext" style="border: 2px; border-style: dotted; border-color: lightgrey; height: '+spacerHeight+'px ;" rel_path="" title=""+><span class="uploadbutton">Click this area to open upload helper...</span></div>');
                                function openFancyUploadHere() {
                                    //alert("upload here!");
                                    var open_dialog = mig_fancyuploadchunked_init("upload_dialog");
                                    var remote_path = $.fn.targetDir($(".fm_files div.filespacer"));
                                    $("#upload_form input[name='remotefilename_0']").val(remote_path);
                                    $("#upload_form input[name='fileupload_0_0_0']").val('');
                                    $("#upload_output").html('');
                                    open_dialog("Upload Files",
                                                function () {
                                                    $(".fm_files").parent().reload('');
                                                }, remote_path, false);
                                    //alert("done upload!");
                                }
                                $("div.uploadspace").click(openFancyUploadHere);
                            }

                            if (t != '/') { // Do not prepend the fake-root.
                                rel_path = t;
                            }
                            //console.debug("update uploadspace with path: "+rel_path);
                            $(".fm_files div.uploadspace").css("height", uploaderHeight+"px")
                                .css("line-height", uploaderHeight+"px")
                                .css("color", "grey")
                                .attr("rel_path", rel_path)
                                .attr("title", rel_path);
                        }

                        // Bind actions to entries in a non-blocking way to avoid
                        // unresponsive script warnings with many entries

                        console.debug('bind action handlers');

                        // Associate drag'n'drop
                        if (options.dragndrop) {
                            console.debug("add drag n drop");
                            /* We can not use .on() directly with draggable - apply
                               recommended workaround from
                               http://stackoverflow.com/questions/1805210/jquery-drag-and-drop-using-live-events
                            */

                            $("#fm_filemanager").on('mouseover',
                                                    "tr.file:not(.ui-draggable), tr.directory:not(.ui-draggable), li.directory:not(.ui-draggable)",
                                                    function() {
                                                        //console.log("adding draggable to elem");
                                                        $(this).draggable({
                                                            cursorAt: { cursor: 'move', left: -10 },
                                                            distance: 5,
                                                            delay: 10,
                                                            helper: function(event) {
                                                                //console.debug("drag src: "+$(this).html());
                                                                /* drag a clone of the first <td> which holds icon and name */
                                                                var drag_elem = $(this).find('td:first').clone();
                                                                drag_elem.attr('rel_path', $(this).attr('rel_path')).css('width', '20px');
                                                                //console.debug("drag elem: "+drag_elem.html());
                                                                return drag_elem;
                                                            }
                                                        });
                                                        //console.log("added draggable to elem");
                                                    });

                            $("#fm_filemanager").on('mouseover',
                                                    "tr.directory:not(.ui-droppable), li.directory:not(.ui-droppable)",
                                                    function() {
                                                        $(this).droppable(
                                                            { greedy: true,
                                                              drop: function(event, ui) {
                                                                  clipboard['is_dir'] = $(ui.helper).hasClass('directoryicon');
                                                                  clipboard['path'] = $(ui.helper).attr(pathAttribute);
                                                                  //console.debug("drop elem: "+clipboard['path']+" : "+clipboard['is_dir']);
                                                                  startProgress("Copying...");
                                                                  copy($(ui.helper).attr('rel_path'),
                                                                       $(this).attr('rel_path'));
                                                              }
                                                            });
                                                    });
                        }

                        // show/hide dotfiles
                        console.debug("refresh dotfiles");
                        refreshDotfiles();

                        // Go to subPath
                        console.debug("navigate to destination path");
                        var current_dir = addressbar.find('input[name=fm_current_path]').val();
                        var first_child = options.subPath.slice(0, options.subPath.indexOf('/'));

                        var descend = false;
                        for (i = 0; i < cur_folder_names.length; i++) {
                            if (first_child == cur_folder_names[i]) {
                                descend = true;
                                break;
                            }
                        }
                        var hit = false;
                        if ((descend == false) && (options.subPath != '')) {
                            for (i = 0; i < cur_file_names.length; i++) {
                                if (options.subPath == cur_file_names[i]) {
                                    hit = true;
                                    break;
                                }
                            }

                            if ((hit == false) && (options.subPath!='')) {
                                // Inform the user
                                $("#cmd_dialog").html('Path does not exist! '
                                                      + current_dir.slice(1)
                                                      + options.subPath);
                                $("#cmd_dialog").dialog(okDialog);
                                $("#cmd_dialog").dialog('open');

                                // Stop trying to find it.
                                options.subPath = '';
                            }

                        }
                        if (descend) {
                            options.subPath = options.subPath.slice(first_child.length+1);
                            /* NOTE: careful to avoid breakage with single quote in paths */
                            $('.fm_folders [rel_path="'+current_dir.slice(1)
                              +first_child+'/"]').click();
                        }
                        console.debug('end ajax handler '+t);
                    }
                });
            }


            function bindContextMenus() {
                var file_menu, directory_menu;
                directory_menu = {
                    "open": {name: "Open Folder", icon: "open"},
                    "mkdir": {name: "Create Folder", icon: "mkdir"},
                    "create": {name: "Create File", icon: "create"},
                    "upload": {name: "Upload File", icon: "upload"},
                    "pack": {name: "Pack", icon: "pack"},
                    "sep1": "---------",
                    //"cut": {name: "Cut", icon: "cut"},
                    "copy": {name: "Copy", icon: "copy"},
                    "paste": {name: "Paste", icon: "paste",
                              disabled: function(key, opt) {
                                  return (!clipboard['path']);
                              }
                             },
                    "rm": {name: "Delete Folder", icon: "rmdir"},
                    "sep2": "---------",
                    "rename": {name: "Rename", icon: "rename"},
                    "sep3": "---------",
                    "imagesettings": {name: "Image Settings", icon: "edit"},
                    "sep4": "---------",
                    "advanced-sub": {
                        "name": "Advanced",
                        icon: "advanced",
                        "items": {
                            "touch": {name: "Update Timestamp (touch)", icon: "touch"},
                            "stat": {name: "File Info (stat)", icon: "stat"},
                            /* TODO: add find support */
                            //"search-sep": "---------",
                            //"find": {name: "Locate File/Folder (find)", icon: "find"},
                        }
                    }
                };
                file_menu = {
                    "show": {name: "Show", icon: "show"},
                    "download": {name: "Download", icon: "download"},
                    "edit": {name: "Edit", icon: "edit"},
                    "sep1": "---------",
                    //"cut": {name: "Cut", icon: "cut"},
                    "copy": {name: "Copy", icon: "copy"},
                    "paste": {name: "Paste", icon: "paste",
                              disabled: function(key, opt) {
                                  return (!clipboard['path']);
                              }
                             },
                    "rm": {name: "Delete", icon: "rm"},
                    "sep2": "---------",
                    "rename": {name: "Rename", icon: "rename"},
                    "pack": {name: "Pack", icon: "pack"},
                    "unpack": {name: "Unpack", icon: "unpack"},
                    /* TODO: add list archive contents */
                    //"listpack": {name: "Show Packed Contents", icon: "listpack"},
                    "sep3": "---------",
                    "advanced-sub": {
                        "name": "Advanced",
                        icon: "advanced",
                        "items": {
                            "cat": {name: "Show All Lines (cat)", icon: "cat"},
                            "head": {name: "Show First Lines (head)", icon: "head"},
                            "tail": {name: "Show Last Lines (tail)", icon: "tail"},
                            "wc": {name: "Word Count (wc)", icon: "wc"},
                            "touch": {name: "Update Timestamp (touch)", icon: "touch"},
                            "stat": {name: "File Info (stat)", icon: "stat"},
                            "truncate": {name: "Clear File (truncate)", icon: "truncate"},
                            "search-sep": "---------",
                            "grep": {name: "Text Search (grep)", icon: "grep"},
                            "shell-sep": "---------",
                            "spell": {name: "Spell Check", icon: "spell"},
                            "md5sum": {name: "MD5 Sum", icon: "md5sum"},
                            "sha1sum": {name: "SHA1 Sum", icon: "sha1sum"},
                            /* TODO: add inline encrypt/decrypt support? */
                            //"encrypt-sep": "---------",
                            //"encrypt": {name: "Encrypt", icon: "encrypt"},
                            //"decrypt": {name: "Decrypt", icon: "decrypt"},
                            "submit-sep": "---------",
                            "submit": {name: "Submit", icon: "submit"}
                        }
                    }
                };
                if (!options["imagesettings"]) {
                    delete directory_menu["imagesettings"];
                    delete directory_menu["sep4"];
                }
                if (!options["enableSubmit"]) {
                    delete file_menu["advanced-sub"]["items"]["submit-sep"];
                    delete file_menu["advanced-sub"]["items"]["submit"];
                }
                if (options["selectOnly"]) {
                    file_menu = {
                        "select": {name: "Select", icon: "select"}
                    };
                    directory_menu = {
                        "select": {name: "Select", icon: "select"}
                    };
                }
                var bind_click = 'right';
                if (touchscreenChecker()) {
                    bind_click = 'left';
                }
                $.contextMenu({
                    selector: 'tr.file',
                    trigger: bind_click,
                    callback: function(key, call_opts) {
                        var m = "file menu clicked: " + key;
                        console.debug(m);
                        var action = key;
                        var el = $(this);
                        console.debug("handle " + action + " on file " + $.fn.dump(el));
                        (options['actions'][action])(action, el, -1);
                        console.debug("done " + action + " on file " + $.fn.dump(el));
                    },
                    items: file_menu
                });

                $.contextMenu({
                    selector: 'tr.directory, li.directory, div.filespacer, div.uploadspace',
                    trigger: bind_click,
                    callback: function(key, call_opts) {
                        var m = "directory menu clicked: " + key;
                        console.debug(m);
                        var action = key;
                        var el = $(this);
                        console.debug("handle " + action + " on dir " + $.fn.dump(el));
                        (options['actions'][action])(action, el, -1);
                        console.debug("done " + action + " on dir " + $.fn.dump(el));
                    },
                    items: directory_menu
                });
            }

            function bindHandlers(folder_pane) {
                bindContextMenus();

                console.debug("add click handler");
                $("#fm_filemanager").on("click",
                                        "tr.file",
                                        function(event) {
                                            clickEvent(this);
                                        });

                console.debug("add dblclick handler");
                //$("#fm_filemanager").off("dblclick", "tr.file, tr.directory");
                $("#fm_filemanager").on("dblclick",
                                        "tr.file, tr.directory",
                                        function(event) {
                                            doubleClickEvent(this);
                                        });

                // bind reload to dotfiles checkbox
                console.debug("bind reload to dotfile checkbox");
                $("#fm_dotfiles[type='checkbox']").on('click',
                                                      function() {
                                                          refreshDotfiles();
                                                      });

                // bind reload to touchscreen checkbox
                console.debug("bind reload to touchscreen checkbox");
                $("#fm_touchscreen[type='checkbox']").on('click',
                                                         function() {
                                                             /* Remove old context menu and reload */
                                                             console.debug('touch reload');
                                                             $.contextMenu('destroy');
                                                             bindContextMenus();
                                                         });

                // Binds: Expands and a call to showbranch
                // or
                // Binds: Collapse
                console.debug("bindBranch");
                //$(folder_pane).off(options.folderEvent, 'li');
                $(folder_pane).on(
                    options.folderEvent,
                    'li',
                    null,
                    function(e) {
                        if ($(this).hasClass('directory')) {
                            if ($(this).hasClass('collapsed')) {
                                // Expand
                                if (!options.multiFolder) {
                                    $(this).parent().find('UL').slideUp(
                                        { duration: options.collapseSpeed,
                                          easing: options.collapseEasing });
                                    $(this).parent().find('LI.directory').removeClass('expanded').addClass('collapsed');
                                }
                                $(this).find('UL').remove(); // cleanup
                                // Go deeper
                                showBranch($(this), $(this).attr('rel_path'));
                                $(this).removeClass('collapsed').addClass('expanded');
                            } else {
                                // Collapse
                                $(this).find('UL').slideUp({ duration: options.collapseSpeed, easing: options.collapseEasing });
                                $(this).removeClass('expanded').addClass('collapsed');
                            }
                        } else {
                            $(this).attr('rel_path');
                        }
                        return false;
                    }
                );
            }


            /*
               Base sorting on the content of the hidden <div> element inside all cells
               ... should be faster than default extraction.
            */
            var myTextExtraction = function(node) {
                return node.childNodes[0].textContent;
            };
            /* TODO: add filter like in example on
               http://mottie.github.io/tablesorter/docs/example-option-show-processing.html
            */
            // showProcessing should show spinner in column head but doesn't seem to work
            $(".fm_files table", obj).tablesorter(
                {showProcessing: true,
                 widgets: ['zebra', 'saveSort'],
                 textExtraction: myTextExtraction,
                 sortColumn: 'Name',
                });

            //TODO: can we catch big sorts and show progress?
            /*
              $(".fm_files table", obj).bind("sortStart", function() {
              console.debug("start table sort")
              startProgress("Sorting entries...");
              }).bind("sortEnd",function() {
              console.debug("done table sort")
              stopProgress();
              });
            */

            // Loading message
            $(".fm_folders", obj).html('<ul class="jqueryFileTree start"><li class="wait">' + options.loadMessage + '<li></ul>\n');

            // Sanitize the subfolder path, simple checks, a malicious user would only hurt himself..

            // Ignore the root
            if (options.subPath == '/') {
                options.subPath = '';
            }

            /**
             * Delegate handlers for file and dir elements.
             *
             */
            var folder_pane = $(".fm_folders", obj);
            bindHandlers(folder_pane);

            showBranch(folder_pane, escape(options.root));

            /*
             * Bind preview buttons
             */

            $("#fm_preview_menubar_zoom_out").on('click',
                                                 function(event) {
                                                     zoom_out_preview();
                                                 });

            $("#fm_preview_menubar_zoom_in").on('click',
                                                function(event) {
                                                    zoom_in_preview();
                                                });

            $("#fm_preview_menubar_refresh").on('click',
                                                function(event) {
                                                    refresh_preview();
                                                });

            $("#preview_histogram_reset_button").on('click',
                                                    function(event) {
                                                        preview.reset();
                                                    });

            $("#preview_histogram_set_cutoff_button").on('click',
                                                         function(event) {
                                                             var histogram_scale = $("#fm_preview_left_tile_histogram_actions input[name=fm_preview_histogram_scale]").val();
                                                             var path = $(".fm_previews input[name=fm_preview_base_path]").val();
                                                             var extension = $(".fm_previews input[name=fm_preview_extension]").val();
                                                             var min_value = $("#fm_preview_left_output input[name='fm_preview_left_output_current_min_value']").val();
                                                             var max_value = $("#fm_preview_left_output input[name='fm_preview_left_output_current_max_value']").val();
                                                             var data;

                                                             // Grey out button as default

                                                             $("#preview_histogram_set_cutoff_button").attr('disabled', true);

                                                             // Get data for update
                                                             // TODO: implement *update* action in filemetaio.py,
                                                             // and replace this get_dir+put_dir

                                                             $.ajax({
                                                                 url: 'filemetaio.py',
                                                                 data: { extension: extension,
                                                                         path: path,
                                                                         output_format: 'json',
                                                                         action: 'get_dir',
                                                                         flags: 'i',
                                                                       },
                                                                 type: "GET",
                                                                 dataType: "json",
                                                                 cache: false,
                                                             }).success(function (jsonRes) {
                                                                 var errors = $(this).renderError(jsonRes);
                                                                 var warnings = $(this).renderWarning(jsonRes);
                                                                 var i;
                                                                 var json_put;

                                                                 if (errors.length > 0) {
                                                                     $("#fm_preview_left_output").html(errors);
                                                                     logger.debug(errors);
                                                                 } else if (warnings.length > 0) {
                                                                     $("#fm_preview_left_output").html(warnings);
                                                                     logger.debug(warnings);
                                                                 }
                                                                 else {
                                                                     for (i = 0; i < jsonRes.length; i++) {
                                                                         if (jsonRes[i].object_type == 'image_setting') {
                                                                             data = jsonRes[i];
                                                                         }
                                                                     }

                                                                     // Update settings with new cutoff values

                                                                     $.ajax({
                                                                         url: 'filemetaio.py',
                                                                         data: { extension: extension,
                                                                                 path: path,
                                                                                 output_format: 'json',
                                                                                 action: 'put_dir',
                                                                                 flags: 'i',
                                                                                 settings_recursive: data['settings_recursive'],
                                                                                 image_type: data['image_type'],
                                                                                 data_type: data['data_type'],
                                                                                 offset: data['offset'],
                                                                                 x_dimension: data['x_dimension'],
                                                                                 y_dimension: data['y_dimension'],
                                                                                 preview_image_extension: data['preview_image_extension'],
                                                                                 preview_x_dimension: data['preview_x_dimension'],
                                                                                 preview_y_dimension: data['preview_y_dimension'],
                                                                                 preview_cutoff_min: min_value,
                                                                                 preview_cutoff_max: max_value,
                                                                               },
                                                                         type: "POST",
                                                                         dataType: "json",
                                                                         cache: false,
                                                                     }).success(function (jsonRes) {
                                                                         var errors = $(this).renderError(jsonRes);
                                                                         var warnings = $(this).renderWarning(jsonRes);
                                                                         var i;
                                                                         if (errors.length > 0) {
                                                                             $("#fm_preview_left_output").html(errors);
                                                                             logger.debug(errors);
                                                                         } else if (warnings.length > 0) {
                                                                             $("#fm_preview_left_output").html(warnings);
                                                                             logger.debug(warnings);
                                                                         }
                                                                     });
                                                                 }
                                                             });

                                                         });

            $("#preview_histogram_auto_button").on('click',
                                                   function(event) {
                                                       alert('Auto pressed');
                                                   });

            /**
             * Bind handlers for forms. This is ridiculous and tedious repetitive code.
             *
             */
            $("#upload_form").ajaxForm(
                {target: '#upload_output', dataType: 'json',
                 success: function(responseObject, statusText) {
                     $("#upload_output").removeClass("info spinner iconspace");
                     var errors = $(this).renderError(responseObject);
                     var warnings = $(this).renderWarning(responseObject);
                     var misc_output = parseWrapped(responseObject, {});
                     if (errors.length > 0) {
                         $("#upload_output").html(errors);
                     } else if (warnings.length > 0) {
                         $("#upload_output").html(warnings);
                     } else {
                         $("#upload_output").html("<p class='info iconspace'>Upload: "+statusText+"</p>" + misc_output);
                     }
                 }
                });

            $("#mkdir_form").ajaxForm(
                {target: '#mkdir_output', dataType: 'json',
                 success: function(responseObject, statusText) {
                     var errors = $(this).renderError(responseObject);
                     var warnings = $(this).renderWarning(responseObject);
                     if (errors.length > 0) {
                         $("#mkdir_output").html(errors);
                     } else if (warnings.length > 0) {
                         $("#mkdir_output").html(warnings);
                     } else {
                         $("#mkdir_dialog").dialog('close');
                         $(".fm_files").parent().reload('');
                     }
                 }
                });

            $("#pack_form").ajaxForm(
                {target: '#pack_output', dataType: 'json',
                 success: function(responseObject, statusText) {
                     var errors = $(this).renderError(responseObject);
                     var warnings = $(this).renderWarning(responseObject);
                     if (errors.length > 0) {
                         $("#pack_output").html(errors);
                     } else if (warnings.length > 0) {
                         $("#pack_output").html(warnings);
                     } else {
                         $("#pack_dialog").dialog('close');
                         $(".fm_files").parent().reload('');
                     }
                 }
                });

            $("#rename_form").ajaxForm(
                {target: '#rename_output', dataType: 'json',
                 success: function(responseObject, statusText) {
                     var errors = $(this).renderError(responseObject);
                     var warnings = $(this).renderWarning(responseObject);
                     if (errors.length > 0) {
                         $("#rename_output").html(errors);
                     } else if (warnings.length > 0) {
                         $("#rename_output").html(warnings);
                     } else {
                         $("#rename_dialog").dialog('close');
                         $(".fm_files").parent().reload('');
                     }
                 },
                 beforeSubmit: function(formData, jqForm, options) {
                     var src = $("#rename_form input[name='src']").val();
                     // Extract the parent of the path
                     var dst = '';
                     // New name of file/dir
                     var newName = $("#rename_form input[name='name']").val();

                     // Extract the parent of the path
                     if (src.lastIndexOf("/") == (src.length-1)) { // is directory?
                         dst = src.substring(0, src.length-1);
                         dst = src.substring(0, dst.lastIndexOf('/'))+'/';
                     } else {
                         dst = src.substring(0, src.lastIndexOf('/'))+'/';
                     }

                     for (var i=0; i<formData.length; i++) {
                         if (formData[i].name == 'dst') {
                             formData[i].value = dst+newName;
                         }
                         if (formData[i].name == 'name') {
                             formData[i].value = '';
                             // Remove the field value otherwise the backend pukes.
                         }
                     }
                     return true;
                 }
                });

            // This is the only form not matching the stuff above
            $("#editor_form").ajaxForm(
                {target: '#editor_output', dataType: 'json',
                 success: function(responseObject, statusText) {
                     var edit_out = '';
                     var errors = $(this).renderError(responseObject);
                     var warnings = $(this).renderWarning(responseObject);
                     // Reset any previous CSS
                     $("#editor_output").removeClass()
                     if (errors.length > 0) {
                         $("#editor_output").addClass("error leftpad");
                         edit_out += errors;
                     } else if (warnings.length > 0) {
                         $("#editor_output").addClass("warn leftpad");
                         edit_out += warnings;
                     } else {
                         $("#editor_output").addClass("ok leftpad");
                         //$("#editor_dialog").dialog('close');
                         $(".fm_files").parent().reload('');
                     }
                     for (var i=0; i<(responseObject.length); i++) {
                         switch(responseObject[i]['object_type']) {
                         case 'text':
                             edit_out += '<span>'+responseObject[i]['text']+'</span><br />';
                             break;
                         case 'submitstatuslist':
                             for (var j=0; j<responseObject[i]['submitstatuslist'].length; j++) {
                                 if (responseObject[i]['submitstatuslist'][j]['status']) {
                                     edit_out += '<span>Submitted as: '+responseObject[i]['submitstatuslist'][j]['job_id']+'</span><br />';
                                 } else {
                                     edit_out += '<span class="errortext">'+responseObject[i]['submitstatuslist'][j]['message']+'</span><br />';
                                 }
                             }
                             break;
                         }
                     }
                     $("#editor_dialog div.spinner").html("").hide();
                     $("#editor_output").html(edit_out);
                     $("#editor_output").addClass("status_box");
                     $(".fm_files").parent().reload('');
                 }
                });
        });
    };

})(jQuery);


/*** Extras for use e.g. in VGrid portals ***/


/*  MiG-Special: initialize a MiG home filechooser dialog, installing the
 *  callback for doubleclick or "select" selection
 *  if files_only is set, directories cannot be chosen
 */
function mig_filechooser_init(name, callback, files_only, start_path) {

    $("#" + name).dialog(
        // see http://jqueryui.com/docs/dialog/ for options
        {autoOpen: false,
         modal: true,
         width: '800px',
         buttons: {"Cancel": function() { $("#" + name).dialog("close"); }
                  }
        });

    var do_d = function(text, action, files) {
        // save and restore original callback and files-mode
        var c = callback;
        var f = files_only;

        $("#" + name).dialog("option", "title", text);

        if (files != undefined) {
            files_only = files;
        }

        if (action == undefined) {
            action = c;
        }

        callback = function(i) { action(i);
                                 files_only = f;
                                 callback = c;
                               };

        $("#" + name).dialog("open");
        /* force reload to get zebra-coloring right (ignored unless visible) */
        $.fn.reload(start_path);
    };
    // code entangled with specific filemanager naming
    var pathAttribute = "rel_path";
    var select_action = function (action, el, pos) {
        var p = $(el).attr(pathAttribute);
        var open_dirs = true;
        if (action != "dclick" && !files_only) {
            open_dirs = false;
        }
        if (open_dirs && $(el).hasClass("directory")) {
            // mimic click on folder pane item if dir is not selectable
            /* NOTE: careful to avoid breakage with single quote in paths */
            $('.fm_folders [rel_path="'+$(el).attr(pathAttribute)+'"]').click();
            return;
        }
        callback(p);
        $("#" + name).dialog("close");
    };

    $("#" + name).filemanager(
        {root: "/",
         connector: "ls.py", params: "path",
         multiFolder: false,
         subPath: (start_path || "/"),
         actions: {select: select_action},
         dragndrop: false,
         filespacer: false,
         uploadspace: false,
         imagesettings: false,
         selectOnly: true
        },
        // doubleclick callback action
        function(el) { select_action("dclick", el, undefined); }
    );
    return do_d;
};


/*  MiG-Special: initialize a local file chooser dialog, installing the
 *  callback for OK and cancel actions.
 */
function local_filechooser_init(name, callback) {

    var ok_action = function (action) {
        var filename = $("#lc_filechooser_file").val();
        callback(filename);
        $("#" + name).dialog("close");
    };

    $("#" + name).dialog(
        // see http://jqueryui.com/docs/dialog/ for options
        {autoOpen: false,
         modal: true,
         width: '800px',
         buttons: {"OK": ok_action,
                   "Close": function() { $("#" + name).dialog("close"); }
                  }
        });

    var do_d = function(text, action) {
        // save and restore original callback
        var c = callback;

        $("#" + name).dialog("option", "title", text);

        if (action == undefined) {
            action = c;
        }

        callback = function(i) { action(i);
                                 callback = c;
                               };

        $("#" + name).dialog("open");
    };

    return do_d;
};

/* expose these helpers in general */

var base_url = "uploadchunked.py?output_format=json;action=";
var upload_url = base_url+"put";
var status_url = base_url+"status";
var delete_url = base_url+"delete";
var move_url = base_url+"move";

$.fn.delete_upload = function(name, dest_dir) {
    console.debug("delete upload: "+name+" "+dest_dir);
    var deleted = false;
    $.ajax({
        url: delete_url,
        dataType: "json",
        data: {"files[]filename": name, "files[]": "dummy",
               "current_dir": dest_dir},
        type: "POST",
        async: false,
        success: function(data, textStatus, jqXHR) {
            //console.debug("delete success handler: "+name);
            //console.debug("data: "+$.fn.dump(data));
            $.each(data, function (index, obj) {
                //console.debug("delete result obj: "+index+" "+$.fn.dump(obj));
                if (obj.object_type == "uploadfiles") {
                    //console.debug("found files in obj "+index);
                    var files = obj.files;
                    $.each(files, function (index, file) {
                        //console.debug("found file entry in results: "+index);
                        if (file.error != undefined) {
                            console.debug("found file error: "+file.error);
                        } else if (file[name]) {
                            //console.debug("found success marker: "+file[name]);
                            deleted = true;
                        }
                        // Break upon first hit
                        return false;
                    });
                }
            });
        }
    });
    //console.debug("return deleted: "+deleted);
    return deleted;
};

$.fn.move_upload = function(name, dest_dir) {
    console.debug("move upload: "+name+" "+dest_dir);
    var moved = false;
    $.ajax({
        url: move_url,
        dataType: "json",
        data: {"files[]filename": name, "files[]": "dummy",
               "current_dir": dest_dir},
        type: "POST",
        async: false,
        success: function(data, textStatus, jqXHR) {
            //console.debug("move success handler: "+name);
            //console.debug("data: "+$.fn.dump(data));
            $.each(data, function (index, obj) {
                //console.debug("move result obj: "+index+" "+$.fn.dump(obj));
                if (obj.object_type == "uploadfiles") {
                    //console.debug("found files in obj "+index);
                    var files = obj.files;
                    $.each(files, function (index, file) {
                        //console.debug("found file entry in results: "+index);
                        if (file.error != undefined) {
                            console.debug("found file error: "+file.error);
                        } else if (file[name]) {
                            //console.debug("found success marker: "+file[name]);
                            moved = true;
                        }
                        // Break upon first hit
                        return false;
                    });
                }
            });
        }
    });
    //console.debug("return moved: "+moved);
    return moved;
};

/* Fancy chunked uploader dialog */
function mig_fancyuploadchunked_init(name, callback) {

    /* TODO:
       move all these dialogs into if jquery section? (fails for some reason)
       drag n drop to fileman drop zone with upload popup?
    */

    console.debug("mig_fancyuploadchunked_init: "+name, callback);
    $.fn.fancyfileupload = $.fn.fileupload;

    $("#" + name).dialog(
        // see http://jqueryui.com/docs/dialog/ for options
        {autoOpen: false,
         modal: true,
         width: '800px',
         position: { my: "top", at: "top+100px", of: window},
         buttons: {
             "Close": function() {
                 /* cancel active uploads if any */
                 if ($(".uploadfileslist button.cancel").length > 0) {
                     showWaitInfo("aborting active uploads", 0, 3000);
                     $(".fileupload-buttons button.cancel").click();
                 }
                 callback();
                 $("#" + name).dialog("close");
             }
         }
        });

    function showMessage(msg, html_msg, fadein_ms, fadeout_ms) {
        if (fadein_ms == undefined) fadein_ms = 0;
        if (fadeout_ms == undefined) fadeout_ms = 10000;
        console.log(msg);
        $("#fancyuploadchunked_output").html(html_msg).fadeIn(fadein_ms,
                                                              function() {
                                                                  $(this).stop();
                                                                  $(this).fadeOut(fadeout_ms);
                                                              }
                                                             );
    }
    function showWaitInfo(msg, fadein_ms, fadeout_ms) {
        var html_msg = "<div class='spinner' style='margin: 20px;'>";
        html_msg += "<span class='iconspace'>"+msg+"</span></div>";
        showMessage("Info: "+msg, html_msg, fadein_ms, fadeout_ms);
    }
    function showInfo(msg, fadein_ms, fadeout_ms) {
        var html_msg = "<div class='info' style='margin: 20px;'>";
        html_msg += "<span class='iconspace'>"+msg+"</span></div>";
        showMessage("Info: "+msg, html_msg, fadein_ms, fadeout_ms);
    }
    function showWarning(msg, fadein_ms, fadeout_ms) {
        var html_msg = "<div class='warn' style='margin: 20px;'>";
        html_msg += "<span class='iconspace'>"+msg+"</span></div>";
        showMessage("Warning: "+msg, html_msg, fadein_ms, fadeout_ms);
    }
    function showError(msg, fadein_ms, fadeout_ms) {
        var html_msg = "<div class='error' style='margin: 20px;'>";
        html_msg += "<span class='iconspace'>"+msg+"</span></div>";
        showMessage("Error: "+msg, html_msg, fadein_ms, fadeout_ms);
    }

    function parseReply(raw_data) {
        var data = {"files": []};
        var target = raw_data;
        //console.debug("parseReply raw data: "+$.fn.dump(raw_data));
        if (raw_data.result != undefined) {
            //console.debug("parseReply found result entry to parse: "+$.fn.dump(raw_data.result));
            target = raw_data.result;
        } else if (raw_data.files != undefined) {
            //console.debug("parseReply return direct files data: "+$.fn.dump(raw_data.files));
            //return raw_data;
            data.files = raw_data.files;
            return data;
        } else {
            console.debug("parseReply falling back to parsing all: "+$.fn.dump(raw_data));
        }
        try {
            $.each(target, function (index, obj) {
                //console.debug("result obj: "+index+" "+$.fn.dump(obj));
                if (obj.object_type == "uploadfiles") {
                    //console.debug("found files in obj "+index);
                    var files = obj.files;
                    //console.debug("found files: "+index+" "+$.fn.dump(files));
                    $.each(files, function (index, file) {
                        //console.debug("found file entry in results: "+index);
                        data["files"].push(file);
                        //console.debug("added upload file: "+$.fn.dump(file));
                    });
                }
            });
        } catch(err) {
            showError("parsing response from server: "+err);
        }
        //console.debug("parsed raw reply into files: "+$.fn.dump(data.files));
        return data;
    }

    var do_d = function(text, action, dest_dir, automatic_dest) {

        console.debug("mig_fancyupload_init do_d: "+text+", "+action+", "+dest_dir);

        // save and restore original callback
        var c = callback;

        //console.debug("mig_fancyupload_init init dialog on: "+$("#"+name));
        $("#" + name).dialog("option", "title", text);

        if (action == undefined) {
            action = c;
        }

        callback = function(i) { action(i);
                                 callback = c;
                               };

        //console.debug("mig_fancyupload_init do_d open");
        $("#" + name).dialog("open");

        //console.debug("mig_fancyupload_init do_d fileupload pre-setup");

        if (automatic_dest) {
            $("#fancyfileuploaddestbox").hide();
        } else {
            $("#fancyfileuploaddestbox").show();
        }

        console.debug("init_fancyupload");
        // Initialize the jQuery File Upload widget:
        //console.debug("mig_uploadchunked_init do_d fileupload setup: "+dest_dir);
        $("#fancyfileuploaddest").val(dest_dir);
        console.debug("init_fancyupload set dest to: "+$("#fancyfileuploaddest").val());
        $(".uploadfileslist").empty();
        $("#fancyfileupload").fancyfileupload({
            // Uncomment the following to send cross-domain cookies:
            //xhrFields: {withCredentials: true},
            url: upload_url,
            dataType: "json",
            maxChunkSize: 32000000, // 32 MB
            filesContainer: ".uploadfileslist",
            maxRetries: 100,
            retryTimeout: 500,
            disableImageLoad: true,
            disableAudioPreview: true,
            disableVideoPreview: true,
            disableValidation: true,
            add: function (e, data) {
                console.debug("add file");
                /* Add final destination for use in done */
                var dest_dir = $("#fancyfileuploaddest").val();
                /* empty dest is not allowed */
                dest_dir = "./" + $.fn.normalizePath(dest_dir);
                data.formData = {current_dir: dest_dir};
                //console.debug("add file with data: "+$.fn.dump(data));
                console.debug("add file with data files: "+$.fn.dump(data.files));
                var that = this;
                try {
                    $.blueimp.fileupload.prototype
                        .options.add.call(that, e, data);
                } catch(err) {
                    showError("adding upload: "+err);
                }
            },
            done: function (e, data) {
                console.debug("done file");
                //console.debug("done with data: "+$.fn.dump(data));
                if (data.result.files == undefined) {
                    var parsed = parseReply(data);
                    //console.debug("done parsed result: "+$.fn.dump(parsed));
                    data.result = parsed;
                }
                //console.debug("done with data result: "+$.fn.dump(data.result));
                /* move files to final destination if so requested */
                console.debug("handle any pending move for done files");
                $.each(data.result.files, function (index, file) {
                    //console.debug("found file entry in results: "+$.fn.dump(file));
                    if (file.error != undefined) {
                        showError("found upload error: "+file.error);
                        // Continue to next iteration on errors
                        return true;
                    }
                    if (!file.moveDest) {
                        // Continue to next if move was not requested
                        return true;
                    }
                    if ($.fn.move_upload(file.name, file.moveDest)) {
                        console.debug("fix path and strip move info: " + file.name);
                        var purename = file.name.substring(file.name.lastIndexOf("/") + 1);
                        var baseurl = file.url.substring(0, file.url.length - file.name.length);
                        file.name = file.moveDest + "/" + purename;
                        file.url = baseurl + file.name;
                        delete file.moveType;
                        delete file.moveDest;
                        delete file.moveUrl;
                        console.debug("updated file entry: "+$.fn.dump(file));
                    } else {
                        showError("automatic move to destination failed!");
                    }
                });
                /* Finally pass control over to native done handler */
                var that = this;
                try {
                    $.blueimp.fileupload.prototype
                        .options.done.call(that, e, data);
                } catch(err) {
                    showError("upload done handler failed: "+err);
                }
            },
            fail: function (e, data) {
                console.debug("fail file");
                // jQuery Widget Factory uses "namespace-widgetname" since version 1.10.0:
                var uploader = $(this).data('blueimp-fileupload') || $(this).data('fileupload');
                var retries = data.context.data('retries') || 0;
                var max_tries = uploader.options.maxRetries;
                if (data.errorThrown != 'abort') {
                    retries += 1;
                    data.context.data('retries', retries);
                    showWarning("upload error in retry no. "+retries+" of "+max_tries, 0, 2000);
                    if (retries <= max_tries) {
                        data.submit();
                        return;
                    }
                }
                data.context.removeData('retries');
                $.each(data.files, function (index, file) {
                    if (file.error != undefined) {
                        showError("uploading of "+file.name+" failed: "+file.error);
                    } else if (data.errorThrown != 'abort' && retries >= max_tries) {
                        console.debug("manually reporting network error for "+file.name);
                        file.error = "gave up after "+retries+" tries (network error?)";
                    } else {
                        console.debug("cancelled file: "+file.name);
                    }
                    console.debug("call clean up file: "+file.name);
                    $.fn.delete_upload(file.name);
                });
                var that = this;
                try {
                    $.blueimp.fileupload.prototype
                        .options.fail.call(that, e, data);
                } catch(err) {
                    showError("upload fail handler failed: "+err);
                }
            }
        });

        // Upload server status check for browsers with CORS support:
        showWaitInfo("checking server availability");
        if ($.support.cors) {
            $.ajax({
                url: status_url,
                dataType: "json",
                type: "POST"
            }).fail(function () {
                console.debug("server status fail");
                $("<div class=\'alert alert-danger\'/>")
                    .text("Upload server currently unavailable - " + new Date())
                    .appendTo("#fancyfileupload");
            }).done(function (raw_result) {
                console.debug("done checking server");
                //var result = parseReply(raw_result);
                //console.debug("done checking server parsed result: "+$.fn.dump(result));
                showInfo("server is ready", 10, 3000);
            }
                   );
        }

        // Load existing files:
        showWaitInfo("loading list of cached uploads");
        $("#fancyfileupload").addClass("fileupload-processing");
        $.ajax({
            // Uncomment the following to send cross-domain cookies:
            //xhrFields: {withCredentials: true},
            url: status_url,
            dataType: "json",
            type: "POST",
            context: $("#fancyfileupload")[0]
        }).always(function () {
            //console.debug("load existing files always handler");
            $(this).removeClass("fileupload-processing");
        }).fail(function () {
            showError("load existing files failed");
        }).done(function (raw_result) {
            //console.debug("loaded existing files: "+$.fn.dump(raw_result));
            var result = parseReply(raw_result);
            console.debug("parsed existing files: "+$.fn.dump(result.files));
            $(this).fileupload("option", "done")
                .call(this, $.Event("done"), {result: result});
            showInfo("list of cached uploads loaded", 10, 3000);
        });

        /* Prevent duplicates in uploadfileslist - old style bind */
        $("#fancyfileupload").on("fileuploadadd", function(e, data) {
            //console.debug("in add handler");
            var current_files = [];
            var path;
            $(this).fileupload("option").filesContainer.children().each(function() {
                //console.debug("in add handler loop");
                if ($(this).data == undefined || $(this).data("data") == undefined) {
                    //showWarning("no this.data field in add handler loop");
                    return true;
                }
                //console.debug("add file in add handler loop");
                path = $(this).data("data").formData.current_dir + "/";
                path += $(this).data("data").files[0].name;
                path = $.fn.normalizePath(path);
                current_files.push(path);
            });
            $(this).fileupload("option").filesContainer.find("td > p.name > a")
                .each(function() {
                    //console.debug("add finished in add handler loop");
                    path = $.fn.normalizePath("./"+$(this).text());
                    current_files.push(path);
                });
            console.debug("found existing uploads: "+current_files);
            data.files = $.map(data.files, function(file, i) {
                path = "./" + $("#fancyfileuploaddest").val() + "/" + file.name;
                path = $.fn.normalizePath(path);
                if ($.inArray(path, current_files) >= 0) {
                    showWarning("ignoring addition of duplicate: "+path);
                    return null;
                }
                return file;
            });
        });

    };

    return do_d;
};

/* Image settings dialog */

function mig_imagesettings_init(name, path, options) {
    var path = path;
    var name = name;

    init_html_and_handlers();

    $("#" + name).dialog(
        // see http://jqueryui.com/docs/dialog/ for options
        {
            autoOpen: false,
            modal: true,
            width: 355,
            position: { my: "top", at: "top+100px", of: window},
            buttons: dialog_list_buttons()
        });

    function dialog_list_buttons() {
        return {
            'New': function() {
                edit(null);
            },
            'Clear': function() {
                remove_all();
            },
            'Refresh': function() {
                show_list();
            },
            'Close': function() {
                $("#" + name).dialog("close");
            }
        };
    }

    function dialog_new_buttons() {
        return {
            'Create': function() {
                $("#imagesettings_form").submit();
            },
            'Cancel': function() {
                show_list();
            },
            'Close': function() {
                $("#" + name).dialog("close");
            }
        };
    }

    function dialog_edit_buttons() {
        return {
            'Update': function() {
                $("#imagesettings_form").submit();
            },
            'Remove': function() {
                remove();
            },
            'Back': function() {
                show_list();
            },
            'Close': function() {
                $("#" + name).dialog("close");
            }
        };
    }

    // Initializes html and handlers

    function init_html_and_handlers() {
        $("#imagesettings_edit").hide();
        $("#imagesettings_list").hide();

        // Handle image settings form submit

        $("#imagesettings_form").ajaxForm(
            {target: '#imagesettings_output', dataType: 'json',
             success: function(responseObject, statusText) {
                 var errors = $(this).renderError(responseObject);
                 var warnings = $(this).renderWarning(responseObject);
                 if (errors.length > 0) {
                     msg = errors;
                     console.debug(errors);
                 } else if (warnings.length > 0) {
                     msg = warnings;
                     console.debug(warnings);
                 } else {
                     msg = 'Image settings updated';
                 }
                 show_list(msg);
             }
            });

        // Only display options for raw data if 'raw' is selected'

        $("#imagesettings_form select[name='image_type']").on('change', function() {
            var value = $("#imagesettings_form select[name='image_type']").val();

            if (value == 'raw') {
                $("#imagesettings_edit_image_type_raw").show({duration: options.expandSpeed,
                                                              easing: options.expandEasing });
            }
            else {
                $("#imagesettings_edit_image_type_raw").hide({duration: options.expandSpeed,
                                                              easing: options.expandEasing });
            }
        });

        // Change Sub-folder checkbox value when checked/unchecked

        $("#imagesettings_form input[name='settings_recursive']").on('change', function() {
            if ($("#imagesettings_form input[name='settings_recursive']").prop("checked")) {
                $("#imagesettings_form input[name='settings_recursive']").val('True');
            }
            else {
                $("#imagesettings_form input[name='settings_recursive']").val('False');
            }
        });
    }

    function show_list(output_msg) {

        // Generate image extension list
        var html_out;

        if (output_msg === undefined) {
            html_out = '';
        }
        else {
            html_out = '<p>' + output_msg + '</p>';
        }
        $("#imagesettings_output").html(html_out);
        $("#imagesettings_list").hide(({duration: options.expandSpeed,
                                        easing: options.expandEasing }));
        $("#imagesettings_edit").hide(({duration: options.expandSpeed,
                                        easing: options.expandEasing }));

        // Retrieve image settings list

        $.ajax({
            url: 'filemetaio.py',
            data: { path: path,
                    output_format: 'json' ,
                    action: 'list',
                    flags: 'i'},
            type: "GET",
            dataType: "json",
            cache: false,
        }).success(function (jsonRes) {
            var errors = $(this).renderError(jsonRes);
            var warnings = $(this).renderWarning(jsonRes);
            if (errors.length > 0) {
                console.debug(errors);
            } else if (warnings.length > 0) {
                console.debug(warnings);
            }

            var i;
            var extension_list = new Array();
            var settings_status_list = new Array();
            var settings_progress_list = new Array();
            var image_count_list = new Array();

            // Generate extension, status, progress and count lists for each entry

            for (i = 0; i < jsonRes.length; i++) {
                if (jsonRes[i].object_type == 'image_settings_list') {
                    extension_list = extension_list.concat(jsonRes[i].extension_list);
                    settings_status_list = settings_status_list.concat(jsonRes[i].settings_status_list);
                    settings_progress_list = settings_progress_list.concat(jsonRes[i].settings_progress_list);
                    image_count_list = image_count_list.concat(jsonRes[i].image_count_list);
                }
            }

            // Generate html for each entry

            var html_out = 'Image file extensions:';
            for (i = 0; i < settings_status_list.length; i++) {
                if (settings_status_list[i].toLowerCase() === 'ready' ||
                    settings_status_list[i].toLowerCase() === 'failed') {
                    html_out += '<ul class="edit">';
                    html_out += '<li title="Edit" ';
                }
                else if (settings_status_list[i].toLowerCase() === 'pending') {
                    html_out += '<ul class="pending">';
                    html_out += '<li title="Pending" ';
                }
                else if (settings_status_list[i].toLowerCase() === 'updating') {
                    html_out += '<ul class="updating">';
                    console.log('mig_imagesettings_init: extension_list[' +i+ ']: ' + extension_list[i] + ' <- updating');
                    html_out += '<li title="Updating" ';
                }
                html_out += 'extension="' + extension_list[i] + '">';
                html_out += '<span style="top:-2px; position:relative;">';
                html_out +=  extension_list[i];
                if (settings_status_list[i].toLowerCase() === 'ready') {
                    html_out += ' (' + image_count_list[i] + ')';
                }
                else if (settings_status_list[i].toLowerCase() === 'updating' ) {
                    html_out +=  ' (' + settings_progress_list[i] + ')';
                }
                else if (settings_status_list[i].toLowerCase() === 'failed' ) {
                    html_out +=  '<span style="color:red"> (Failed)</span>';
                }

                html_out += '</li></scan></ul>';
            }
            $("#imagesettings_list").html(html_out);

            // Attach 'edit' handler to each list element

            $("#imagesettings_list ul.edit li").click(function() {
                edit($(this).attr('extension'));
            });

            // Show list

            $("#imagesettings_list").show(({duration: options.expandSpeed,
                                            easing: options.expandEasing}));

            // Set dialog buttons

            $("#" + name).dialog('option', 'buttons', dialog_list_buttons());
        });
    }

    // Removes all element from list

    function remove_all() {
        $.ajax({
            url: 'filemetaio.py',
            data: { path: path,
                    output_format: 'json' ,
                    action: 'remove_dir',
                    flags: 'i'},
            type: "GET",
            dataType: "json",
            cache: false,
            type: "GET",
            dataType: "json",
            cache: false,
        }).success(function (jsonRes) {
            console.log('imagesettings edit jsonRes.length: ' + jsonRes.length);
            var i;
            var errors = $(this).renderError(jsonRes);
            var warnings = $(this).renderWarning(jsonRes);
            var msg = '';

            if (errors.length > 0) {
                msg = errors;
                console.debug(msg);
            } else if (warnings.length > 0) {
                msg = warnings;
                console.debug(msg);
            } else {
                msg = 'Image Settings Cleared';
            }
            show_list(msg);
        });
    }

    // Remove an element from list

    function remove() {
        var extension = $("#imagesettings_form input[name='extension']").val();
        $.ajax({
            url: 'filemetaio.py',
            data: { path: path,
                    output_format: 'json' ,
                    action: 'remove_dir',
                    extension: extension,
                    flags: 'i'},
            type: "GET",
            dataType: "json",
            cache: false,
            dataType: "json",
            cache: false,
        }).success(function (jsonRes) {
            var i;
            var errors = $(this).renderError(jsonRes);
            var warnings = $(this).renderWarning(jsonRes);
            var msg = '';

            if (errors.length > 0) {
                msg = errors;
                console.debug(msg);
            } else if (warnings.length > 0) {
                msg = warnings;
                console.debug(msg);
            } else {
                msg = "Image setting for: '" + extension + "'' removed";
            }
            show_list(msg);
        });
    }

    // Prepare edit image setting data

    function edit(extension) {
        var edit_form_values = {
            extension: '',
            settings_status: 'Pending',
            settings_recursive: 'False',
            image_type: 'raw',
            data_type: 'float32',
            offset: 0,
            x_dimension: 0,
            y_dimension: 0,
            preview_cutoff_min: 0.0,
            preview_cutoff_max: 0.0,
        };
        if (extension === null) {
            do_edit(edit_form_values)
        }
        else {
            $.ajax({
                url: 'filemetaio.py',
                data: { extension: extension,
                        path: path,
                        output_format: 'json',
                        action: 'get_dir',
                        flags: 'i',
                      },
                type: "GET",
                dataType: "json",
                cache: false,
            }).success(function (jsonRes) {
                console.log('imagesettings edit jsonRes.length: ' + jsonRes.length);
                var i;
                var errors = $(this).renderError(jsonRes);
                var warnings = $(this).renderWarning(jsonRes);

                if (errors.length > 0) {
                    $("#imagesettings_output").html(errors);
                    console.debug(errors);
                } else if (warnings.length > 0) {
                    $("#imagesettings_output").html(warnings);
                    console.debug(warnings);
                }

                for (i = 0; i < jsonRes.length; i++) {
                    if (jsonRes[i].object_type == 'image_setting') {
                        edit_form_values['extension'] = jsonRes[i]['extension'];
                        edit_form_values['settings_recursive'] = jsonRes[i]['settings_recursive'];
                        edit_form_values['image_type'] = jsonRes[i]['image_type'];
                        edit_form_values['data_type'] = jsonRes[i]['data_type'];
                        edit_form_values['offset'] = jsonRes[i]['offset'];
                        edit_form_values['x_dimension'] = jsonRes[i]['x_dimension'];
                        edit_form_values['y_dimension'] = jsonRes[i]['y_dimension'];
                        edit_form_values['preview_cutoff_min'] = jsonRes[i]['preview_cutoff_min'];
                        edit_form_values['preview_cutoff_max'] = jsonRes[i]['preview_cutoff_max'];
                    }
                }
                do_edit(edit_form_values);
            });
        }
    }

    // Handle edit image setting

    function do_edit(edit_form_values) {
        $("#imagesettings_output").html('');

        $("#imagesettings_list").hide(({duration: options.expandSpeed,
                                        easing: options.expandEasing }));
        $("#imagesettings_edit").hide(({duration: options.expandSpeed,
                                        easing: options.expandEasing }));

        // Fill edit html form

        $("#imagesettings_form input[name='path']").val(path);
        $("#imagesettings_form input[name='flags']").val('i');
        $("#imagesettings_form input[name='action']").val('put_dir');
        $("#imagesettings_form input[name='settings_status']").val(edit_form_values['settings_status']);
        $("#imagesettings_form input[name='extension']").val(edit_form_values['extension']);
        if (edit_form_values['extension'] !== '') {
            $("#imagesettings_form input[name='extension']").attr("readonly", true);
        }
        else {
            $("#imagesettings_form input[name='extension']").attr("readonly", false);
        }
        if (edit_form_values['settings_recursive'] == 'True') {
            $("#imagesettings_form input[name='settings_recursive']").prop('checked', true).change();
        }
        else {
            $("#imagesettings_form input[name='settings_recursive']").prop('checked', false).change();
        }
        $("#imagesettings_form select[name='image_type']").val(edit_form_values['image_type']).prop('selected', true).change();
        if (edit_form_values['data_type'] !== 'None') {
            $("#imagesettings_form select[name='data_type']").val(edit_form_values['data_type']).prop('selected', true);
        }
        $("#imagesettings_form input[name='offset']").val(edit_form_values['offset']);
        $("#imagesettings_form input[name='x_dimension']").val(edit_form_values['x_dimension']);
        $("#imagesettings_form input[name='y_dimension']").val(edit_form_values['y_dimension']);
        $("#imagesettings_form input[name='preview_cutoff_min']").val(edit_form_values['preview_cutoff_min']);
        $("#imagesettings_form input[name='preview_cutoff_max']").val(edit_form_values['preview_cutoff_max']);

        // Show edit html form

        $("#imagesettings_edit").show({duration: options.expandSpeed,
                                       easing: options.expandEasing});

        // Set dialog buttons

        if (edit_form_values['extension'] === '') {
            $("#" + name).dialog('option', 'buttons', dialog_new_buttons());
        }
        else {
            $("#" + name).dialog('option', 'buttons', dialog_edit_buttons());
        }
    }

    // Initial function used for when opening dialog

    var do_d = function(text) {

        console.log('mig_imagesettings dialog: ' + name + ', ' + text + ', ' + path);
        $("#" + name).dialog("open");

        show_list();
    };

    return do_d;
};
