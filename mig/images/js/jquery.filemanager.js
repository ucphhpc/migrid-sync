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

/* 
   Make sure we can always use console.log without scripts crashing. IE<=9
   does not init it unless in developer mode and things thus randomly fail
   without a trace.
*/
if (!window.console) {
  var noOp = function(){}; // no-op function
  console = {
    log: noOp,
    warn: noOp,
    error: noOp
  }
}

if (jQuery) (function($){
  
    var pathAttribute = 'rel_path';
    var doSort = true;

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
        // make sure tablesorter style is applied
        setTimeout(function() {
            $(".fm_files table").trigger("update");
        }, 10);
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
                errors +='<span class="errortext">'+jsonRes[i].text+'</span><br />';
        }
        return errors;
    }

    $.fn.renderWarning = function(jsonRes) {
        
        var warnings = '';
        
        for (var i=0; i<jsonRes.length; i++) {
            if (jsonRes[i]['object_type'] == 'warning')
                warnings +='<span class="warningtext">'+jsonRes[i].text+'</span><br />';
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
        $(".fm_folders [rel_path='"+reloadPath+"']").click();
        $(".fm_folders [rel_path='"+reloadPath+"']").click();
        
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
         $(".fm_addressbar input[name='fm_current_path']").val(path);
         $.fn.reload(path);
    }

    /* extended this by the "clickaction" callback, which can remain undefined...
     * the provided callback will be executed on doubleclick
     */
    $.fn.filemanager = function(user_options, clickaction) {
    
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
        
        function doubleClickEvent(el) {
            if (clickaction != undefined) {
                clickaction(el);
                return;
            } 
            // if no clickaction is provided, default to opening and showing
            if ($(el).hasClass('directory')) {
                $(".fm_folders [rel_path='"+$(el).attr(pathAttribute)+"']").click();
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
            $("#cmd_dialog").html('<p class="spinner" style="padding-left: 26px;">Copying... "'+src+'" <br />To: "'+dst+'"</p>');           
            
            $.post('cp.py', { src: src,
                                 dst: dst,
                                 output_format: 'json',
                                 flags: flag
                               },
                      function(jsonRes, textStatus) {
                          var errors = $(this).renderError(jsonRes);
                          var warnings = $(this).renderWarning(jsonRes);
                          if (errors.length > 0) {
                              $($("#cmd_dialog").html('<p>Error:</p>'+errors));
                          } else if (warnings.length > 0) {
                              $($("#cmd_dialog").html('<p>Warning:</p>'+warnings));
                          } else {
                              // Only reload if destination is current folder
                              if ($(".fm_addressbar input[name='fm_current_path']").val().substr(1) == dst.substring(0, dst.lastIndexOf('/'))+'/')
                                  $(".fm_files").parent().reload($(".fm_addressbar input[name='fm_current_path']").val().substr(1));
                              $("#cmd_dialog").dialog('close');
                          }
                      }, "json"
                  );

        }
        
        function jsonWrapper(el, dialog, url, jsonOptions) {
            
            var jsonSettings = { path: $(el).attr(pathAttribute),
                                 output_format: 'json' };
            
            $.fn.extend(jsonSettings, jsonOptions);
            
            /* We used to use $.getJSON() here but now some back ends require POST */
            $.post(url, jsonSettings,
                      function(jsonRes, textStatus) {
                          
                          var errors = $(this).renderError(jsonRes);
                          var warnings = $(this).renderWarning(jsonRes);
                          var file_output = $(this).renderFileoutput(jsonRes);
                          var misc_output = '';
                          
                          for (var i = 0; i < jsonRes.length; i++) {
                              if (jsonRes[i]['object_type'] == 'submitstatuslist') {
                                  for (j = 0; j < jsonRes[i]['submitstatuslist'].length; j++) {
                                      if (jsonRes[i]['submitstatuslist'][j]['status']) {
                                          misc_output +=  '<p>Submitted "'
                                              + jsonRes[i]['submitstatuslist'][j]['name']
                                              + '"</P>'
                                              + '<p>Job identfier: "'+jsonRes[i]['submitstatuslist'][j]['job_id']
                                              + '"</p>';
                                      } else {
                                          misc_output +=  '<p>Failed submitting:</p><p>'
                                              + jsonRes[i]['submitstatuslist'][j]['name']
                                              + ' '+jsonRes[i]['submitstatuslist'][j]['message']
                                              + '</p>';
                                      }                                                   
                                  }
                              }
                          }
                          
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
                          } else {
                              $(".fm_files").parent().reload($(this).parentPath($(el).attr(pathAttribute))); 
                          }
                      }, "json"
                  );
        }
      
        // Callback helpers for context menu
        var callbacks = {
            
            show:   function (action, el, pos) { 
                window.open('/cert_redirect/'+$(el).attr(pathAttribute))
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
                    window.open('/cert_redirect/'+$(el).attr(pathAttribute))
                } else {
                    document.location = 
                        'cat.py?path='
                        +$(el).attr(pathAttribute)+'&output_format=file';
                }
            },
            edit:   function (action, el, pos) {
                $("#editor_dialog textarea[name='editarea']").val('');
                $("#editor_output").removeClass()
                $("#editor_output").addClass("hidden");
                $("#editor_output").html('');                
                $("#editor_dialog").dialog(
                    { buttons: {
                          'Save Changes': function() {
                              $("#editor_dialog div.spinner").html("Saving file...").show();
                              $("#editor_form").submit(); },
                          Close: function() {
                              $(this).dialog('close');},
                          Download: function() { 
                              document.location = 
                                  'cat.py?path='
                                  +$(el).attr(pathAttribute)
                                  +'&output_format=file'; }
                      },
                      autoOpen: false, closeOnEscape: true,
                      modal: true, width: '800px'}
                                                                    );
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
                $("#editor_dialog").dialog(
                    { buttons: {
                          'Save Changes': function() {
                              $("#editor_dialog div.spinner").html("Saving file...").show();
                              $("#editor_form").submit(); },
                          Close: function() {
                              $(this).dialog('close');} 
                      },
                      autoOpen: false, closeOnEscape: true,
                      modal: true, width: '800px'}
            
                );
            
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
            zip:    function (action, el, pos) { 
                /* zip file or directory to user specified file */
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
            
                // Initialize the form
                $("#zip_form input[name='current_dir']").val(current_dir);
                $("#zip_form input[name='src']").val(path_name);
                $("#zip_form input[name='dst']").val(path_name + '.zip');
                $("#zip_output").html('');
                $("#zip_dialog").dialog(
                    { buttons: {
                          Ok: function() { 
                              $("#zip_form").submit(); },
                          Cancel: function() {
                              $(this).dialog('close');}
                      },
                      autoOpen: false, closeOnEscape: true,
                      modal: true}
                );
                $("#zip_dialog").dialog('open');

            },
            unzip:   function (action, el, pos) { 
                var dst = $(".fm_addressbar input[name='fm_current_path']").val();
                // unzip uses src instead of path parameter
                jsonWrapper(el, '#cmd_dialog', 'unzip.py', {dst: dst, src: $(el).attr(pathAttribute), path: ''}); 
            },
            submit: function (action, el, pos) { 
                jsonWrapper(el, '#cmd_dialog', 'submit.py'); },
            copy:   function (action, el, pos) {
                clipboard['is_dir'] = $(el).hasClass('directory');
                clipboard['path'] = $(el).attr(pathAttribute);
            },
            paste:  function (action, el, pos) {
                copy(clipboard['path'], $(el).attr(pathAttribute));
            },
            rm:     function (action, el, pos) {
            
                var flags = '';
                var rm_path = $(el).attr(pathAttribute);
                if ($(el).attr(pathAttribute).lastIndexOf('/') == $(el).attr(pathAttribute).length-1) {
                    flags = 'r';
                }
                $("#cmd_dialog").html('<p><span class="ui-icon ui-icon-alert" style="float:left; margin:0 7px 20px 0;"></span>"'+rm_path+'" will be permanently deleted. Are you sure?</p></div>');
                $("#cmd_dialog").dialog(
                    { buttons: {
                          Ok: function() { 
                              $(this).dialog('close');
                              jsonWrapper(el, '#cmd_dialog', 'rm.py', 
                                          {flags: flags});
                          },
                          Cancel: function() { 
                              $(this).dialog('close'); }
                      },
                      width: '800px', autoOpen: false,
                      closeOnEscape: true, modal: true});
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
                $("#mkdir_dialog").dialog(
                    { buttons: {
                          Ok: function() { 
                              $("#mkdir_form").submit(); 
                              $(".fm_files").parent().reload('');
                          },
                          Cancel: function() {
                              $(this).dialog('close');}
                      },
                      autoOpen: false, closeOnEscape: true,
                      modal: true}
                );
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
                $("#rename_dialog").dialog(
                    { buttons: {
                          Ok: function() { 
                              $("#rename_form").submit();
                              $(".fm_files").parent().reload('');
                          },
                          Cancel: function() {
                              $(this).dialog('close');}
                      },
                      autoOpen: false, closeOnEscape: true,
                      modal: true}
                );
                $("#rename_dialog").dialog('open');
            }
        };

    /* TODO: enable dragndrop after fixing issue with 
       - single click on a file enables drag even after mouse up
       - after double click any move of the cursor result in drag
    */

    var defaults = {
        root: '/',      
        connector: 'somewhere.py',
        param: 'path',
        folderEvent: 'click',  
        expandSpeed: 500,
        collapseSpeed: 500,
        expandEasing: null,
        collapseEasing: null,
        multiFolder: true,
        loadMessage: 'Loading...',
        actions: callbacks,
        subPath: '/',
        dragndrop: false,
        filespacer: true
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

         var file_pane = $(".fm_files", obj);        
         var statusbar = $(".fm_statusbar", obj);
         var path_breadcrumbs = $("#fm_xbreadcrumbs", obj);
         var addressbar = $(".fm_addressbar", obj);
         var timestamp = 0;
         var emptyDir = true;
         var bc_html = '';
         var entry_html = '';
         var onclick_action = '';
         var subdir_path = t;
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
             onclick_action = "$.fn.openDir('"+subdir_path+"');return false;";
             entry_html = '  <li '+li_class+'>';
             entry_html += '    <a href="?path='+subdir_path+'" '+a_class;
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
                
         $(folder_pane).addClass('wait');
          
         statusbar.html('<span class="spinner" style="padding-left: 20px;">loading directory entries...</span>');
         $.ajax({
                url: options.connector,
                type: "GET",
                dataType: "json",
                data: { path: t, output_format: 'json', flags: 'fa' },
                cache: false,
                success: function(jsonRes, textStatus) {
          //console.log($.now()+' begin ajax handler '+t);

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
          
          statusbar.html('updating directory entries...');
          var folders = '';

          // Root node if not already created
          if (t == '/' && $(".fm_folders li.userhome").length == 0) {
              folders += '<ul class="jqueryFileTree"><li class="directory expanded userhome recent" rel_path="/" title="Home"><div>/</div>\n';
          }

          // Regular nodes from here on after
          folders += '<ul class="jqueryFileTree">\n';

          var total_file_size = 0;
          var file_count = 0.0;          
          var is_dir = false;
          var base_css_style = 'file';
          var icon = '';
          var dotfile = '';
          var entry_title = '';
          var entry_html = '', entries_html = '';

          var dir_prefix = '';
          var path = '';
          
          $(".fm_files table tbody").empty();
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
              if (is_dir) {
                  base_css_style = 'directory';
                  icon = 'directoryicon ' + listing[i]['extra_class'];

                  path += '/';
                  folders +=  '<li class="recent ' + icon + ' ' + dotfile + 
                      ' ' + base_css_style + ' collapsed" rel_path="' + path +
                      '" title="' + entry_title + '"><div>' +
                      listing[i]['name'] + '</div></li>\n';
                  dir_prefix = '##';
                  
                  cur_folder_names.push(listing[i]['name']);
                  
              }
              else {
                  icon = 'fileicon';
                  cur_file_names.push(listing[i]['name']);
              }

              /* manually build entry to reduce risk of script timeout warnings
                 from excessive html DOM manipulation. Mark the entry as
                 recent to ease targetted context menu and drag n' drop later.
                 Finally append it all in one go to save a lot of overhead.
              */
              entry_html = '<tr class="recent ' + base_css_style + ' ' + dotfile + 
                  '" title="' + entry_title + '" rel_path="' + path + '">' + 
                  '<td style="padding-left: 20px;" class="' + icon + ' ext_' + 
                  listing[i]['file_info']['ext'] + '"><div>' + dir_prefix +
                  listing[i]['name'] + '</div>' + listing[i]['name'] +
                  '</td>' + '<td><div class="bytes">' + listing[i]['file_info']['size'] +
                  '</div>' + pp_bytes(listing[i]['file_info']['size']) +
                  '</td>' + '<td><div>' + listing[i]['file_info']['ext'] +
                  '</div>' + listing[i]['file_info']['ext'] + '</td>'+
                  '<td><div>' + listing[i]['file_info']['created'] + '</div>' +
                  pp_date(listing[i]['file_info']['created']) + '</td>' +
                  '</tr>';
              entries_html += entry_html;
              emptyDir = false;
            }
            $(".fm_files table tbody").append(entries_html);

            folders += '</ul>\n';

            // End the root node
            if (t == '/') {
                folders += '</li></ul>\n';
            } 

            // Prefix '/' for the visual presentation of the current path.
            if (t.substr(0, 1) == '/') {
                addressbar.find("input[name='fm_current_path']").val(t);  
            } else {
                addressbar.find("input[name='fm_current_path']").val('/'+t);  
            }

            folder_pane.removeClass('wait');

            // Update statusbar
            statusbar.html(file_count+' files in current folder of total '+pp_bytes(total_file_size)+' in size.');

            folder_pane.append(folders);
            //$("#fm_debug").html("<textarea cols=200 rows=15>"+$.fn.dump($(".fm_folders [rel_path='/']"))+"\n"+$(".fm_folders").html()+"</textarea>").show();

            // Inform tablesorter of new data
            var sorting = [[0, 0]]; 
            $(".fm_files table").trigger("update");
            if (!emptyDir)  { // Don't try and sort an empty table, this causes error!
                if (doSort)  { // only first time now that we use saveSort
                    $(".fm_files table").trigger("sorton", [sorting]);
                    doSort = false;
                }
            }

            if (options.root == t) {
                //if (options.root == t+'/') {
                folder_pane.find('UL:hidden').show();
            } else {
                folder_pane.find('UL:hidden').slideDown(
                    { duration: options.expandSpeed, 
                      easing: options.expandEasing });
            }

            /* UI stuff: contextmenu, drag'n'drop. */
            
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
                    //console.log("add filespacer");
                    $(".fm_files").append('<div class="filespacer" style="height: '+spacerHeight+'px ;" rel_path="" title=""+></div>');
                }
                
                if (t != '/') { // Do not prepend the fake-root.
                    rel_path = t;
                }
                //console.log("update filespacer with path: "+rel_path);
                $(".fm_files div.filespacer").css("height", spacerHeight+"px")
                                             .attr("rel_path", rel_path)
                                             .attr("title", rel_path);

                $("div.filespacer").contextMenu(
                    { menu: 'folder_context',
                    leftButtonChecker: touchscreenChecker},
                    function(action, el, pos) {
                        (options['actions'][action])(action, el, pos);                                            
                    });
            }
            if (options.uploadspace) {
                if (!options.filespacer)
                    uploaderHeight = extraHeight;
                else
                    uploaderHeight = extraHeight/2;
                var rel_path = "";
                /* add or update existing uploadspace */
                if ($(".fm_files div.uploadspace").length == 0) {
                    //console.log("add uploadspace");
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
                //console.log("update uploadspace with path: "+rel_path);
                $(".fm_files div.uploadspace").css("height", uploaderHeight+"px")
                                             .css("line-height", uploaderHeight+"px")
                                             .css("color", "grey")
                                             .attr("rel_path", rel_path)
                                             .attr("title", rel_path);
            }

            // Bind actions to entries in a non-blocking way to avoid 
            // unresponsive script warnings with many entries

            // Associate context menus in the background for responsiveness
            $("tr.recent.directory, li.recent.directory div").each(function() { 
                var t = $(this); 
                setTimeout(function() {
                    t.contextMenu(
                        { menu: 'folder_context',
                          leftButtonChecker: touchscreenChecker},
                        function(action, el, pos) {
                            if ($(el).tagName() == 'DIV') {
                                (options['actions'][action])(action, el.parent(), pos);
                            } else {
                                (options['actions'][action])(action, el, pos);
                            }                                                                                           
                        })
                }, 10);
            });

            $("tr.recent.file").each(function() { 
                var t = $(this); 
                setTimeout(function() {
                    t.contextMenu(
                        { menu: 'file_context',
                          leftButtonChecker: touchscreenChecker},
                        function(action, el, pos) {
                            (options['actions'][action])(action, el, pos);
                        })
                }, 10);
            });

            // Doubleclick actions (including preventing text select on dclick)
            /* TODO: can we migrate mousedown select prevention to .on() too? */
            $("tr.recent.file, tr.recent.directory").each(function() { 
                var t = $(this); 
                setTimeout(function() {
                    t.mousedown(function(event) { event.preventDefault(); });
                    //t.dblclick(function(event) { doubleClickEvent(this); });
                }, 10);
            });
            
            $("#fm_filemanager").on("dblclick", 
                                    "tr.file, tr.directory",
                                    function(event) {
                                        doubleClickEvent(this);
                                    }); 
            /* 
            $("#fm_filemanager").on("mousedown",  
                                    "tr.file, tr.directory",
                                    function(event) { event.preventDefault(); }); 
            */

            // Associate drag'n'drop
            if (options.dragndrop) {
                $("tr.recent.file, tr.recent.directory, li.recent.directory").each(function() { 
                    var t = $(this);                     
                    setTimeout(function() {
                        t.draggable(
                            {
                            cursorAt: { cursor: 'move', top: 0, left: -10 },
                             distance: 5,
                             helper: function(event) {
                                 return $("<div style='display: block;'>&nbsp;</div>")
                                     .attr('rel_path', $(this).attr('rel_path'))
                                     .attr('class', $(this).attr('class'))
                                     .css('width', '20px');
                             }
                            }
                        )
                    }, 10);

                });

                $("tr.recent.directory, li.recent.directory").each(function() { 
                    var t = $(this); 
                    setTimeout(function() {
                        t.droppable(
                            { greedy: true,
                              drop: function(event, ui) {
                                  clipboard['is_dir'] = $(ui.helper).hasClass('directory');
                                  clipboard['path'] = $(ui.helper).attr(pathAttribute);
                                  copy($(ui.helper).attr('rel_path'), 
                                       $(this).attr('rel_path'));
                              }
                            })
                    }, 10);
                });
            }

            // show/hide dotfiles
            refreshDotfiles();

            // remove recent markers
            $("tr.recent, li.recent").each(function() { 
                var t = $(this); 
                setTimeout(function() {
                    t.removeClass('recent');
                }, 10);
            });

            // bind reload to dotfiles checkbox - just use old bind style here
            $("#fm_dotfiles[type='checkbox']").on('click',
                function() {
                    refreshDotfiles();
                });

            // Binds: Expands and a call to showbranch
            // or
            // Binds: Collapse
            bindBranch(folder_pane);                    

            // Go to subPath                    
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
            if ((descend == false) && (options.subPath!='')) {
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
                $(".fm_folders [rel_path='"+current_dir.slice(1)
                  +first_child+"/']").click();                       
            }
            //console.log($.now()+' end ajax handler '+t);
          }
       });
     }
     
     
     function bindBranch(t) {
         $(t).off(options.folderEvent, 'li');
         $(t).on(
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
     };
                            
     // Base sorting on the content of the hidden <div> element
     var myTextExtraction = function(node) {  
         return node.childNodes[0].innerHTML; 
     };
     $(".fm_files table", obj).tablesorter(
         {widgets: ['zebra', 'saveSort'],
          textExtraction: myTextExtraction,
          sortColumn: 'Name'});

     // Loading message
     $(".fm_folders", obj).html('<ul class="jqueryFileTree start"><li class="wait">' + options.loadMessage + '<li></ul>\n');
            
     // Sanitize the subfolder path, simple checks, a malicious user would only hurt himself..
            
     // Ignore the root
     if (options.subPath == '/') {
         options.subPath = '';
     }
     
     showBranch($(".fm_folders", obj), escape(options.root));
     
       
     /**
      * Bind handlers for forms. This is ridiculous and tedious repetitive code.
      *
      */
     $("#upload_form").ajaxForm(
         {target: '#upload_output', dataType: 'json',
          success: function(responseObject, statusText) {
              var errors = $(this).renderError(responseObject);
              var warnings = $(this).renderWarning(responseObject);
              if (errors.length > 0) {
                  $("#upload_output").html(errors);
              } else if (warnings.length > 0) {
                  $("#upload_output").html(warnings);
              } else {
                  $("#upload_dialog").dialog('close');
                  $(".fm_files").parent().reload($("#upload_form input[name='remotefilename_0']").val().substr(2));
              }
          }
          /*
          ,
          error: function(responseObject, status, err){
              var errors = 'upload error: '+responseObject.status+' ; '+status+' ; '+err;
              $("#upload_output").html(errors);
          }
          */
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
 
     $("#zip_form").ajaxForm(
         {target: '#zip_output', dataType: 'json',
          success: function(responseObject, statusText) {
              var errors = $(this).renderError(responseObject);
              var warnings = $(this).renderWarning(responseObject);
              if (errors.length > 0) {
                  $("#zip_output").html(errors);
              } else if (warnings.length > 0) {
                  $("#zip_output").html(warnings);
              } else {
                  $("#zip_dialog").dialog('close');
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
         }
     );
                        
     // This is the only form not matching the stuff above
     $("#editor_form").ajaxForm(
         {target: '#editor_output', dataType: 'json',
          success: function(responseObject, statusText) {
              var edit_out ='';
              var errors = $(this).renderError(responseObject);
              var warnings = $(this).renderWarning(responseObject);
              // Reset any previous CSS
              $("#editor_output").removeClass()
              if (errors.length > 0) {
                  $("#editor_output").addClass("error").css("padding-left", "20px");;
                  edit_out += errors;
              } else if (warnings.length > 0) {
                  $("#editor_output").addClass("warn").css("padding-left", "20px");;
                  edit_out += warnings;
              } else {
                  $("#editor_output").addClass("ok").css("padding-left", "20px");;
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
           width: 800, 
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
                    $(".fm_folders [rel_path='"+$(el).attr(pathAttribute)+"']").click();
                    return;
                }
                callback(p);
                $("#" + name).dialog("close");
    };
    
    $("#" + name).filemanager(
         {root: "/",
          connector: "ls.py", params: "path",
          expandSpeed: 0, collapseSpeed: 0, multiFolder: false,
          subPath: (start_path || "/"),
          actions: {select: select_action},
          dragndrop: false,
          filespacer: false,
          uploadspace: false
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
           width: 800,
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
    console.log("delete upload: "+name+" "+dest_dir);
    var deleted = false;
    $.ajax({
        url: delete_url,
            dataType: "json",
        data: {"files[]filename": name, "files[]": "dummy",
               "current_dir": dest_dir},
        type: "POST",
        async: false,
        success: function(data, textStatus, jqXHR) {
            //console.log("delete success handler: "+name);
            //console.log("data: "+$.fn.dump(data));
            $.each(data, function (index, obj) {
                //console.log("delete result obj: "+index+" "+$.fn.dump(obj));
                if (obj.object_type == "uploadfiles") {
                    //console.log("found files in obj "+index);
                    var files = obj.files;
                    $.each(files, function (index, file) {
                        //console.log("found file entry in results: "+index);
                        if (file.error != undefined) {
                            console.log("found file error: "+file.error);
                        } else if (file[name]) {
                            //console.log("found success marker: "+file[name]);
                            deleted = true;
                        }
                        // Break upon first hit
                        return false;
                    });
                }
            });
        }
    });
    //console.log("return deleted: "+deleted);
    return deleted;
};

$.fn.move_upload = function(name, dest_dir) {
    console.log("move upload: "+name+" "+dest_dir);
    var moved = false;
    $.ajax({
        url: move_url,
        dataType: "json",
        data: {"files[]filename": name, "files[]": "dummy",
               "current_dir": dest_dir},
        type: "POST",
        async: false,
        success: function(data, textStatus, jqXHR) {
            //console.log("move success handler: "+name);
            //console.log("data: "+$.fn.dump(data));
            $.each(data, function (index, obj) {
                //console.log("move result obj: "+index+" "+$.fn.dump(obj));
                if (obj.object_type == "uploadfiles") {
                    //console.log("found files in obj "+index);
                    var files = obj.files;
                    $.each(files, function (index, file) {
                        //console.log("found file entry in results: "+index);
                        if (file.error != undefined) {
                            console.log("found file error: "+file.error);
                        } else if (file[name]) {
                            //console.log("found success marker: "+file[name]);
                            moved = true;
                        }
                        // Break upon first hit
                        return false;
                    });
                }
            });
        }
    });
    //console.log("return moved: "+moved);
    return moved;
};

/* Fancy chunked uploader dialog */
function mig_fancyuploadchunked_init(name, callback) {

    /* TODO: 
       move all these dialogs into if jquery section? (fails for some reason)
       drag n drop to fileman drop zone with upload popup?
    */

    console.log("mig_fancyuploadchunked_init: "+name, callback);
    $.fn.fancyfileupload = $.fn.fileupload;

    $("#" + name).dialog(
        // see http://jqueryui.com/docs/dialog/ for options
          {autoOpen: false,
           modal: true,
           width: 800,
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
        html_msg += "<span style='margin-left: 20px;'>"+msg+"</span></div>";
        showMessage("Info: "+msg, html_msg, fadein_ms, fadeout_ms);
    }
    function showInfo(msg, fadein_ms, fadeout_ms) {
        var html_msg = "<div class='info' style='margin: 20px;'>";
        html_msg += "<span style='margin-left: 20px;'>"+msg+"</span></div>";
        showMessage("Info: "+msg, html_msg, fadein_ms, fadeout_ms);
    }
    function showWarning(msg, fadein_ms, fadeout_ms) {
        var html_msg = "<div class='warn' style='margin: 20px;'>";
        html_msg += "<span style='margin-left: 20px;'>"+msg+"</span></div>";
        showMessage("Warning: "+msg, html_msg, fadein_ms, fadeout_ms);
    }
    function showError(msg, fadein_ms, fadeout_ms) {
        var html_msg = "<div class='error' style='margin: 20px;'>";
        html_msg += "<span style='margin-left: 20px;'>"+msg+"</span></div>";
        showMessage("Error: "+msg, html_msg, fadein_ms, fadeout_ms);
    }

    function parseReply(raw_data) {
        var data = {"files": []};
        var target = raw_data;
        //console.log("parseReply raw data: "+$.fn.dump(raw_data));
        if (raw_data.result != undefined) {
            //console.log("parseReply found result entry to parse: "+$.fn.dump(raw_data.result));
            target = raw_data.result;
        } else if (raw_data.files != undefined) {
             //console.log("parseReply return direct files data: "+$.fn.dump(raw_data.files));
             //return raw_data;
             data.files = raw_data.files;
             return data;
        } else {
            console.log("parseReply falling back to parsing all: "+$.fn.dump(raw_data));            
        }
        try {
            $.each(target, function (index, obj) {
                //console.log("result obj: "+index+" "+$.fn.dump(obj));
                if (obj.object_type == "uploadfiles") {
                    //console.log("found files in obj "+index);
                    var files = obj.files;
                    //console.log("found files: "+index+" "+$.fn.dump(files));
                    $.each(files, function (index, file) {
                        //console.log("found file entry in results: "+index);
                        data["files"].push(file);
                        //console.log("added upload file: "+$.fn.dump(file));
                    });
                }
            });
        } catch(err) {
            showError("parsing response from server: "+err);
        }
        //console.log("parsed raw reply into files: "+$.fn.dump(data.files));
        return data;
    }
    
    var do_d = function(text, action, dest_dir, automatic_dest) {

        console.log("mig_fancyupload_init do_d: "+text+", "+action+", "+dest_dir);

        // save and restore original callback
        var c = callback;

        //console.log("mig_fancyupload_init init dialog on: "+$("#"+name));
        $("#" + name).dialog("option", "title", text);

        if (action == undefined) {
            action = c;
        }

        callback = function(i) { action(i);
                                 callback = c;
                               };

        //console.log("mig_fancyupload_init do_d open");
        $("#" + name).dialog("open");

        //console.log("mig_fancyupload_init do_d fileupload pre-setup");

        if (automatic_dest) { 
            $("#fancyfileuploaddestbox").hide();
        } else {
            $("#fancyfileuploaddestbox").show();
        }

        console.log("init_fancyupload");
        // Initialize the jQuery File Upload widget:
        //console.log("mig_uploadchunked_init do_d fileupload setup: "+dest_dir);
        $("#fancyfileuploaddest").val(dest_dir);
        console.log("init_fancyupload set dest to: "+$("#fancyfileuploaddest").val());
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
                console.log("add file");
                /* Add final destination for use in done */ 
                var dest_dir = $("#fancyfileuploaddest").val();
                /* empty dest is not allowed */
                dest_dir = "./" + $.fn.normalizePath(dest_dir);
                data.formData = {current_dir: dest_dir};
                //console.log("add file with data: "+$.fn.dump(data));
                console.log("add file with data files: "+$.fn.dump(data.files));
                var that = this;
                try {
                    $.blueimp.fileupload.prototype
                                .options.add.call(that, e, data);
                } catch(err) {
                    showError("adding upload: "+err);
                }
            },
            done: function (e, data) {
                console.log("done file");
                //console.log("done with data: "+$.fn.dump(data));
                if (data.result.files == undefined) {
                    var parsed = parseReply(data);
                    //console.log("done parsed result: "+$.fn.dump(parsed));
                    data.result = parsed;
                }
                //console.log("done with data result: "+$.fn.dump(data.result));
                /* move files to final destination if so requested */
                console.log("handle any pending move for done files");
                $.each(data.result.files, function (index, file) {
                    //console.log("found file entry in results: "+$.fn.dump(file));
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
                        console.log("fix path and strip move info: " + file.name);
                        var purename = file.name.substring(file.name.lastIndexOf("/") + 1);
                        var baseurl = file.url.substring(0, file.url.length - file.name.length);
                        file.name = file.moveDest + "/" + purename;
                        file.url = baseurl + file.name;
                        delete file.moveType;
                        delete file.moveDest;
                        delete file.moveUrl;
                        console.log("updated file entry: "+$.fn.dump(file));
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
                console.log("fail file");
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
                        console.log("manually reporting network error for "+file.name);
                        file.error = "gave up after "+retries+" tries (network error?)";
                    } else {
                        console.log("cancelled file: "+file.name);
                    }
                    console.log("call clean up file: "+file.name);
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
                console.log("server status fail");
                $("<div class=\'alert alert-danger\'/>")
                    .text("Upload server currently unavailable - " + new Date())
                    .appendTo("#fancyfileupload");
            }).done(function (raw_result) {
                        console.log("done checking server");
                        //var result = parseReply(raw_result);
                        //console.log("done checking server parsed result: "+$.fn.dump(result));
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
            //console.log("load existing files always handler");
            $(this).removeClass("fileupload-processing");
        }).fail(function () {
            showError("load existing files failed");
        }).done(function (raw_result) {
                    //console.log("loaded existing files: "+$.fn.dump(raw_result));
                    var result = parseReply(raw_result);
                    console.log("parsed existing files: "+$.fn.dump(result.files));
                    $(this).fileupload("option", "done")
                        .call(this, $.Event("done"), {result: result});
                    showInfo("list of cached uploads loaded", 10, 3000);
                });

        /* Prevent duplicates in uploadfileslist - old style bind */
        $("#fancyfileupload").on("fileuploadadd", function(e, data) {
            //console.log("in add handler");
            var current_files = [];
            var path;
            $(this).fileupload("option").filesContainer.children().each(function() {
                //console.log("in add handler loop");
                if ($(this).data == undefined || $(this).data("data") == undefined) {
                    //showWarning("no this.data field in add handler loop");
                    return true;
                }
                //console.log("add file in add handler loop");
                path = $(this).data("data").formData.current_dir + "/";
                path += $(this).data("data").files[0].name;
                path = $.fn.normalizePath(path);
                current_files.push(path);
            });
            $(this).fileupload("option").filesContainer.find("td > p.name > a")
                .each(function() {
                    //console.log("add finished in add handler loop");
                    path = $.fn.normalizePath("./"+$(this).text());
                    current_files.push(path);
                });
            console.log("found existing uploads: "+current_files);
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

