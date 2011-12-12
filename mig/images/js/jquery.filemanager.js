if (jQuery) (function($){
  
    // Use touchscreen interface without need for right clicking
    function touchscreenChecker() {
        var touchscreen = $("#fm_touchscreen input[type='checkbox']").is(":checked");

        return touchscreen;
    }

    $.fn.dump = function(element) {
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
                errors +='<p>'+jsonRes[i].text+'</p>';
        }
        return errors;
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

    $.fn.reload = function reload(path) {
        var reloadPath = path;
        
        if (reloadPath == '') {
            reloadPath = $('.fm_addressbar input[name=fm_current_path]').val().substr(1);
        }
        
        // Make sure slash remains for home
        if (reloadPath == '') {
            reloadPath = '/';
        }

        // Trigger the click-event twice for obtaining the original state (collapse+expand).
        $('.fm_folders [rel_path='+reloadPath+']').click();
        $('.fm_folders [rel_path='+reloadPath+']').click();
        
    }
    
    
    /* extended this by the "clickaction" callback, which can remain undefined...
     * the provided callback will be executed on doubleclick
     */
    $.fn.filemanager = function(user_options, clickaction) {
    
        var pathAttribute = 'rel_path';
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
                $('.fm_folders [rel_path='+$(el).attr(pathAttribute)+']').click();
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
            
            $('#cmd_dialog').dialog(okDialog);
            $('#cmd_dialog').dialog('open');
            $('#cmd_dialog').html('<p class="spinner" style="padding-left: 26px;">Copying... "'+src+'" <br />To: "'+dst+'"</p>');           
            
            $.post('cp.py', { src: src,
                                 dst: dst,
                                 output_format: 'json',
                                 flags: flag
                               },
                      function(jsonRes, textStatus) {
                          
                          var errors = $(this).renderError(jsonRes);
                          if (errors.length > 0) {
                              $($('#cmd_dialog').html('<p>Error:</p>'+errors));
                          } else {
                              // Only reload if destination is current folder
                              if ($('.fm_addressbar input[name=fm_current_path]').val().substr(1) == dst.substring(0, dst.lastIndexOf('/'))+'/')
                                  $('.fm_files').parent().reload($('.fm_addressbar input[name=fm_current_path]').val().substr(1));
                              $('#cmd_dialog').dialog('close');
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
                              || (file_output.length > 0) 
                              || (misc_output.length > 0)) {
                              
                              $(dialog).dialog(okDialog);
                              $(dialog).dialog('open');

                              if (file_output.length > 0) {
                                  file_output = '<pre>'+file_output+'</pre>'; 
                              }
                              
                              $(dialog).html(errors+file_output+misc_output);
                          } else {
                              $('.fm_files').parent().reload($(this).parentPath($(el).attr(pathAttribute))); 
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
                
                $("#editor_dialog textarea[name=editarea]").val('');
                $('#editor_dialog').dialog('destroy');
                $('#editor_output').html('');
                $("#editor_dialog").dialog(
                    { buttons: {
                          'Save Changes': function() { 
                              $('#editor_form').submit(); },
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
                $("#editor_dialog div.spinner").show();
                $("#editor_dialog input[name=submitjob]").attr('checked', false);
                $("#editor_dialog input[name=path]").val('./'+$(el).attr(pathAttribute));
                $("#editor_dialog").dialog('open');             
                
                // Grab file info
                $.getJSON('cat.py',
                          { path: $(el).attr(pathAttribute),
                            output_format: 'json' },
                          function(jsonRes, textStatus) {
                    
                              var file_output = '';
                              for (i = 0; i < jsonRes.length; i++) {
                                  if (jsonRes[i].object_type=='file_output') {
                                      for (j = 0; j < jsonRes[i].lines.length; j++) {
                                          file_output += jsonRes[i].lines[j];
                                      }
                                  }
                              }

                              $("#editor_dialog textarea[name=editarea]").val(file_output);
                              $("#editor_dialog div.spinner").hide();

                          });
                
            },
            create:     function (action, el, pos) {
                
                $('#editor_dialog').dialog('destroy');
                $('#editor_output').html('');
                $("#editor_dialog").dialog(
                    { buttons: {
                          'Save Changes': function() {
                              $('#editor_form').submit(); },
                          Close: function() {
                              $(this).dialog('close');} 
                      },
                      autoOpen: false, closeOnEscape: true,
                      modal: true, width: '800px'}
            
                );
            
                // determine file-name of new file with fallback to default in
                // current dir if dir is empty
                var new_file_name = $('.fm_addressbar input[name=fm_current_path]').val()+'new_empty_file-1';
                var name_taken = true;

                for (var i=1; name_taken; i++) {
                    name_taken = false;
                    $('#fm_filelisting tbody tr').each(function(item) {
                        if ($(this).attr('rel_path') == $(el).attr(pathAttribute)+'new_empty_file'+'-'+i) {
                            name_taken = true;                          
                        } else {
                            new_file_name = $(el).attr(pathAttribute)+'new_empty_file'+'-'+i;
                        }
                    });
                    
                }

                $("#editor_dialog input[name=submitjob]").attr('checked', false);
                $("#editor_dialog input[name=path]").val('./'+new_file_name);
                $("#editor_dialog textarea[name=editarea]").val('');
                $("#editor_dialog div.spinner").hide();
                $("#editor_dialog").dialog('open');             
                
            },
            cat:    function (action, el, pos) { 
                jsonWrapper(el, '#cmd_dialog', 'cat.py'); },
            head:   function (action, el, pos) { 
                jsonWrapper(el, '#cmd_dialog', 'head.py'); },
            tail:   function (action, el, pos) { 
                jsonWrapper(el, '#cmd_dialog', 'tail.py'); },
            zip:   function (action, el, pos) { 
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
                $('#zip_form input[name=current_dir]').val(current_dir);
                $('#zip_form input[name=src]').val(path_name);
                $('#zip_form input[name=dst]').val(path_name + '.zip');
                $("#zip_output").html('');
                $("#zip_dialog").dialog('destroy');
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
                var dst = $('.fm_addressbar input[name=fm_current_path]').val();
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
                $('#cmd_dialog').dialog('destroy');
                $('#cmd_dialog').html('<p><span class="ui-icon ui-icon-alert" style="float:left; margin:0 7px 20px 0;"></span>"'+rm_path+'" will be permanently deleted. Are you sure?</p></div>');
                $('#cmd_dialog').dialog(
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
                $('#cmd_dialog').dialog('open');
            },
            upload: function (action, el, pos) {
                
                var remote_path = $(el).attr(pathAttribute);
                if (remote_path == '/') {
                    remote_path = './';                                             
                } else {
                    remote_path = './'+remote_path;
                }
                $("#upload_form input[name=remotefilename_0]").val(remote_path);
                $("#upload_form input[name=fileupload_0_0_0]").val('');
                $("#upload_output").html('');
                $("#upload_dialog").dialog(
                    {buttons: {
                         Upload: function() { 
                             $('#upload_form').submit(); 
                             $('.fm_files').parent().reload('');
                         },
                         Cancel: function() {
                             $(this).dialog('close');}
                     },
                     autoOpen: false, closeOnEscape:  true,
                     modal: true, width: '800px'});
                $('#upload_dialog').dialog('open');
            },
            mkdir:  function (action, el, pos) {
                                
                // Initialize the form
                $('#mkdir_form input[name=current_dir]').val($(el).attr(pathAttribute));
                $('#mkdir_form input[name=path]').val('');
                $('#mkdir_output').html('');
                
                $("#mkdir_dialog").dialog('destroy');
                $("#mkdir_dialog").dialog(
                    { buttons: {
                          Ok: function() { 
                              $('#mkdir_form').submit(); 
                              $('.fm_files').parent().reload('');
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
                $('#rename_form input[name=src]').val($(el).attr(pathAttribute));
                $('#rename_form input[name=name]').val(path_name);
                $("#rename_output").html('');
                $("#rename_dialog").dialog('destroy');
                $("#rename_dialog").dialog(
                    { buttons: {
                          Ok: function() { 
                              $("#rename_form").submit();
                              $('.fm_files').parent().reload('');
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
        subPath: '/'
    };
    var options = $.extend(defaults, user_options);
    
    // reestablish defaults for undefined actions:
    $.each(callbacks, function(name, fct) {
               if (options['actions'][name] == undefined) {
                   options['actions'][name] = callbacks[name];
               } // else { alert(name + " overloaded");}
           });

    return this.each(function() {
     obj = $(this);

     // Create the tree structure on the left and populate the table
     // list of files on the right
     function showBranch(folder_pane, t) {

         var file_pane = $('.fm_files', obj);        
         var statusbar = $('.fm_statusbar', obj);
         var path_breadcrumbs = $('#fm_xbreadcrumbs', obj);
         var addressbar = $('.fm_addressbar', obj);
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
             onclick_action = "$('.fm_addressbar input[name=fm_current_path]').val('"+subdir_path+"');";
             onclick_action += "$.fn.reload('"+subdir_path+"');";
             entry_html = '  <li '+li_class+'>';
             entry_html += '    <a href="#" '+a_class+' onclick="'+onclick_action+'">'+subdir_name+'</a>';
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

         statusbar.html('loading directory entries...');
         $.getJSON(options.connector,
                   { path: t, output_format: 'json', flags: 'fa' },
                   function(jsonRes, textStatus) {
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
          if (t == '/' && $('.fm_folders li.userhome').length == 0) {
              folders += '<ul class="jqueryFileTree"><li class="directory expanded userhome recent" rel_path="/" title="Home"><div>/</div>\n';
          }

          // Regular nodes from here on after
          folders += '<ul class="jqueryFileTree">\n';

          var total_file_size = 0;
          var file_count = 0.0;          
          var is_dir = false;
          var base_css_style = 'file';
          var icon = '';
          var entry_title = '';
          var entry_html = '';

          var dir_prefix = '';
          var path = '';
          
          $('.fm_files table tbody').empty();
          $(".jqueryFileTree.start").remove();
          $('.fm_files div').remove();
          for (i = 0; i < listing.length; i++) {
            
              // ignore the pseudo-dirs
              if ((listing[i]['name'] == '.') ||
                  (listing[i]['name'] == '..')) {
                  continue;
              }
              
              is_dir = listing[i]['type'] == 'directory';
              base_css_style = 'file';
              icon = '';
              dir_prefix = '__';
                        
              // Stats for the statusbar
              file_count++;
              total_file_size += listing[i]['file_info']['size'];
                                                
              path = listing[i]['name'];
              if (t != '/') { // Do not prepend the fake-root.
                  path = t+path;  
              }

              entry_title = path + ' ' + listing[i]['special'];
              if (is_dir) {
                  base_css_style = 'directory';
                  icon = 'directoryicon ' + listing[i]['extra_class'];

                  path += '/';
                  folders +=  '<li class="recent ' + icon + ' ' +
                      base_css_style + ' collapsed" rel_path="' + path +
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
                 recent to ease targetted context menu and drag n' drop later
              */
              entry_html = '<tr class="recent ' + base_css_style +
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
              $('.fm_files table tbody').append($(entry_html)
                                                .dblclick(function() { doubleClickEvent(this); }));
              emptyDir = false;
          }

            folders += '</ul>\n';

            // End the root node
            if (t == '/') {
                folders += '</li></ul>\n';
            }
            
            // Prefix '/' for the visual presentation of the current path.
            if (t.substr(0, 1) == '/') {
                addressbar.find('input[name=fm_current_path]').val(t);  
            } else {
                addressbar.find('input[name=fm_current_path]').val('/'+t);  
            }
            
            folder_pane.removeClass('wait');
            folder_pane.append(folders);
            //$("#fm_debug").html("<textarea cols=200 rows=15>"+$.fn.dump($('.fm_folders [rel_path=/]'))+"\n"+$(".fm_folders").html()+"</textarea>").show();

            // Inform tablesorter of new data
            var sorting = [[0, 0]]; 
            $(".fm_files table").trigger("update");
            if (!emptyDir)  { // Don't try and sort an empty table, this causes error!
                $(".fm_files table").trigger("sorton", [sorting]);
            }
            
            // Update statusbar
            statusbar.html(file_count+' files in current folder of total '+pp_bytes(total_file_size)+' in size.');

            if (options.root == t) {
                //if (options.root == t+'/') {
                folder_pane.find('UL:hidden').show();
            } else {
                folder_pane.find('UL:hidden').slideDown(
                    { duration: options.expandSpeed, 
                      easing: options.expandEasing });
            }

            /* UI stuff: contextmenu, drag'n'drop. */
            
            // Create an element for the whitespace below the list of files in the file pane
            // Always preserve a small space for pasting into the folder, etc
            var headerHeight = 20;
            var spacerHeight = 40;
            if ($("#fm_filelisting").height() + spacerHeight < $(".fm_files").height() - headerHeight) {
                spacerHeight = $(".fm_files").height() - $("#fm_filelisting").height() - headerHeight;
            }

            if (t != '/') { // Do not prepend the fake-root.
                $('.fm_files').append('<div class="filespacer" style="height: '+spacerHeight+'px ;" rel_path="'+t+'" title="'+t+'"+></div>');
            } else {
                $('.fm_files').append('<div class="filespacer" style="height: '+spacerHeight+'px ;" rel_path="" title=""></div>');  
            }

            $("div.filespacer").contextMenu(
                    { menu: 'folder_context',
                    leftButtonChecker: touchscreenChecker},
                    function(action, el, pos) {
                        (options['actions'][action])(action, el, pos);                                            
                    });
            
            // Bind actions to entries in a non-blocking way to avoid 
            // unresponsive script warnings with many entries

            // Associate context menus
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
            
            // Associate drag'n'drop
            $('tr.recent.file, tr.recent.directory, li.recent.directory').each(function() { 
                var t = $(this); 
                setTimeout(function() {
                        t.draggable(
                            {cursorAt: 
                             { cursor: 'move', top: 0, left: -10 },
                             distance: 5,
                             helper: function(event) {
                                 return $('<div style="display: block;">&nbsp;</div>')
                                     .attr('rel_path', $(this).attr('rel_path'))
                                     .attr('class', $(this).attr('class'))
                                     .css('width', '20px');
                             }
                            }
                        )
                }, 10);
            });

            $('tr.recent.directory, li.recent.directory').each(function() { 
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

            // remove recent markers
            $('tr.recent, li.recent').each(function() { 
                var t = $(this); 
                setTimeout(function() {
                    t.removeClass('recent');
                }, 10);
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
                    $('#cmd_dialog').html('Path does not exist! '
                                          + current_dir.slice(1)
                                          + options.subPath);
                    $('#cmd_dialog').dialog(okDialog);
                    $('#cmd_dialog').dialog('open');

                    // Stop trying to find it.
                    options.subPath = '';
                }
                
            }
            if (descend) {
                options.subPath = options.subPath.slice(first_child.length+1);
                $('.fm_folders [rel_path='+current_dir.slice(1)
                  +first_child+'/]').click();                       
            }
            
        });
 
     }
      
     function bindBranch(t) {
         $(t).find('LI').bind(
             options.folderEvent,
             function() {
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
         
         // Prevent A from triggering the # on non-click events
         if (options.folderEvent.toLowerCase != 'click') {
             $(t).find('LI').bind('click', function() { return false; });
         }
         
     };
                            
     // Base sorting on the content of the hidden <div> element
     var myTextExtraction = function(node) {  
         return node.childNodes[0].innerHTML; 
     };
     $('.fm_files table', obj).tablesorter(
         {widgets: ['zebra'],
          textExtraction: myTextExtraction,
          sortColumn: 'Name'});

     // Loading message
     $('.fm_folders', obj).html('<ul class="jqueryFileTree start"><li class="wait">' + options.loadMessage + '<li></ul>\n');
            
     // Sanitize the subfolder path, simple checks, a malicious user would only hurt himself..
            
     // Ignore the root
     if (options.subPath == '/') {
         options.subPath = '';
     }
     
     showBranch($('.fm_folders', obj), escape(options.root));
            
     /**
      * Bind handlers for forms. This is ridiculous and tedious repetitive code.
      *
      */
     $('#upload_form').ajaxForm(
         {target: '#upload_output', dataType: 'json',
          success: function(responseObject, statusText) {
              var errors = $(this).renderError(responseObject);
              if (errors.length > 0) {
                  $('#upload_output').html(errors);
              } else {
                  $('.fm_files').parent().reload($('#upload_form input[name=remotefilename_0]').val().substr(2));
                  $('#upload_dialog').dialog('close');
              }
          }
         });
            
     $('#mkdir_form').ajaxForm(
         {target: '#mkdir_output', dataType: 'json',
          success: function(responseObject, statusText) {
              var errors = $(this).renderError(responseObject);
              if (errors.length > 0) {
                  $('#mkdir_output').html(errors);
              } else {
                  $('#mkdir_dialog').dialog('close');
                  $('.fm_files').parent().reload('');
              }
          }
         });
 
     $('#zip_form').ajaxForm(
         {target: '#zip_output', dataType: 'json',
          success: function(responseObject, statusText) {
              var errors = $(this).renderError(responseObject);
              if (errors.length > 0) {
                  $('#zip_output').html(errors);
              } else {
                  $('#zip_dialog').dialog('close');
                  $('.fm_files').parent().reload('');
              }
          }
     });

     $('#rename_form').ajaxForm(
         {target: '#rename_output', dataType: 'json',
          success: function(responseObject, statusText) {
              var errors = $(this).renderError(responseObject);
              if (errors.length > 0) {
                  $('#rename_output').html(errors);
              } else {
                  $('#rename_dialog').dialog('close');
                  $('.fm_files').parent().reload('');
              }
          },
          beforeSubmit: function(formData, jqForm, options) {
              var src = $('#rename_form input[name=src]').val();
              // Extract the parent of the path
              var dst = '';
              // New name of file/dir
              var newName = $('#rename_form input[name=name]').val();
              
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
     $('#editor_form').ajaxForm(
         {target: '#editor_output', dataType: 'json',
          success: function(responseObject, statusText) {
              var stuff ='';
              for (var i=0; i<(responseObject.length); i++) {
                  switch(responseObject[i]['object_type']) {
                  case 'text':
                      stuff += '<p>'+responseObject[i]['text']+'</p>';    
                      break;
                  case 'submitstatuslist':
                      for (var j=0; j<responseObject[i]['submitstatuslist'].length; j++) {
                          if (responseObject[i]['submitstatuslist'][j]['status']) {
                              stuff += '<p>Submitted as: '+responseObject[i]['submitstatuslist'][j]['job_id']+'</p>';
                          } else {
                              stuff += '<p style="color: red;">'+responseObject[i]['submitstatuslist'][j]['message']+'</p>';
                          }
                      }
                      break;
                  }
              }
              $('#editor_output').html(stuff);
              $('.fm_files').parent().reload('');
          }
         });
    });
        
  };

})(jQuery);



/*  MiG-Special: initialize a filechooser dialog, installing the
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
                if (files_only && $(el).hasClass("directory")) {
                    $("#" + name).reload($(el).attr(pathAttribute));
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
          actions: {select: select_action}
         },
         // doubleclick callback action
         function(el) { select_action(undefined, el, undefined); }
    );
    return do_d;
};

