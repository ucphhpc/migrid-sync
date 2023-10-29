/*

  #
  # --- BEGIN_HEADER ---
  #
  # jquery.ajaxhelpers - jquery based ajax helpers for managers
  # Copyright (C) 2003-2023  The MiG Project lead by Brian Vinter
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

/* Enable strict mode to help catch tricky errors early */
"use strict";


var center_class="class='centertext'";
var title_class="class='title'";
var border_class="class='border'";
function base_td(content) {
    return "<td>"+content+"</td>";
}
function attr_td(content, attr_helper) {
    return "<td "+attr_helper+">"+content+"</td>";
}
function center_td(content) {
    return attr_td(content, center_class);
}
function title_td(content) {
    return attr_td(content, title_class);
}
function border_td(content) {
    return attr_td(content, border_class);
}

function format_url(url) {
    return '<a class="link" href="'+url+'">'+url+'</a>';
}

function format_link(link_item) {
    var link = '<a ';
    if (link_item.id !== undefined) {
        link += 'id="'+link_item.id+'" ';
    }
    if (link_item.class !== undefined) {
        link += 'class="'+link_item.class+'" ';
    }
    if (link_item.title !== undefined) {
        link += 'title="'+link_item.title+'" ';
    }
    if (link_item.target !== undefined) {
        link += 'target="'+link_item.target+'" ';
    }
    link += 'href="'+link_item.destination+'">';
    if (link_item.text !== undefined) {
        link += link_item.text;
    }
    link += '</a>';
    return link;
}

function makeSpareFields(target, name, min_spare) {
    /* Make sure that at least spare_fields empty input fields are available 
       for name in target form */
    var elem_str = target+" input[name='"+name+"']";
    //console.debug("fields "+$(elem_str));
    var field = '<input type="text" class="fillwidth padspace" '+
        'name="'+name+'" value="" />';
    var min_spare = min_spare || 2;
    var spare_fields = 0;
    $(elem_str).each(function(i) {
        if ($(this).val() === "") {
            spare_fields += 1;
        }
    });
    //console.debug("add field check with "+spare_fields+" spare fields");
    for (var i=spare_fields; i<min_spare; i++) {
        //console.debug("adding spare field for "+target+" "+name);
        $(target).append(field+'<br />');
    }
}

function handle_ajax_error(jqXHR, textStatus, errorThrown, name, operation, statusElem) {
    /* Shared helper to detect if session expired and react with complete page
       reload, or display other errors in the statusElem. */
    console.error(name+" "+operation+" failed: "+errorThrown);
    $(statusElem).removeClass("spinner iconleftpad");
    $(statusElem).empty();
    /* TODO: narrow down by checking redirect url against openid servers? */
    /* NOTE: empty error and rejected state hints at expired session */
    if (errorThrown === "" && jqXHR.state() === "rejected") {
        console.error("fail looks like session time out - reload for login!");
        $(statusElem).append("<span class=\'warningtext\'>"+
                             "Error: session expired - force re-login</span>");
        /* Reload entire page for proper login and redirection */
        setTimeout("location.reload()", 2000);
    } else {
        /* Just display any other errors */
        $(statusElem).append("<span class=\'errortext\'>"+
                             "Error: "+errorThrown+"</span>");
    }
}

function ajax_redb() {
    console.debug("load runtime envs");
    var tbody_elem = $("#runtimeenvtable tbody");
    //console.debug("empty table");    
    $(tbody_elem).empty();
    $("#ajax_status").addClass("spinner iconleftpad");
    $("#ajax_status").html("Loading runtime envs ...");
    /* Request runtime envs list in the background and handle as soon as
    results come in */
    $.ajax({
      url: "?output_format=json&operation=list",
      type: "GET",
      dataType: "json",
      cache: false,
      success: function(jsonRes, textStatus) {
          console.debug("got response from list");
          var chunk_size = 200;
          var table_entries = "", error = "";
          var i, j;
          var rte, rte_hint, entry;
          /* Grab results from json response and insert items in table */
          for (i=0; i<jsonRes.length; i++) {
              //console.debug("looking for content: "+ jsonRes[i].object_type);
              if (jsonRes[i].object_type === "error_text") {
                  console.error("list: "+jsonRes[i].text);
                  error += jsonRes[i].text;
              } else if (jsonRes[i].object_type === "runtimeenvironments") {
                  var runtimeenvs = jsonRes[i].runtimeenvironments;
                  for (j=0; j<runtimeenvs.length; j++) {
                      rte = runtimeenvs[j];
                      //console.info("found runtimeenv: "+rte.name);
                      var viewlink = format_link(rte.viewruntimeenvlink);
                      var dellink = "";
                      if (rte.ownerlink !== undefined) {
                          dellink = format_link(rte.ownerlink);
                      }
                      rte_hint = center_class+" title='"+rte.providers+"'";
                      entry = "<tr>"+base_td(rte.name)+center_td(viewlink)+
                          center_td(dellink)+base_td(rte.description)+
                          attr_td(rte.resource_count, rte_hint)+
                          base_td(rte.created)+
                          "</tr>";
                      //console.debug("append entry: "+entry);
                      table_entries += entry;
                      /* chunked updates - append after after every chunk_size entries */
                      if (j > 0 && j % chunk_size === 0) {
                          console.debug('append chunk of ' + chunk_size + ' entries');
                          $(tbody_elem).append(table_entries);
                          table_entries = "";
                      }
                  }
              }
          }
          if (table_entries) {
              console.debug('append remaining chunk of ' + (j % chunk_size) + ' entries');
              $(tbody_elem).append(table_entries);
          }
          $("#ajax_status").removeClass("spinner iconleftpad");
          $("#ajax_status").empty();
          if (error) {
              $("#ajax_status").append("<span class=\'errortext\'>"+
                                       "Error: "+error+"</span>");
          }
          $("#runtimeenvtable").trigger("update");

      },
      error: function(jqXHR, textStatus, errorThrown) {
          handle_ajax_error(jqXHR, textStatus, errorThrown, "redb", "list",
                            "#ajax_status");
      }
  });
}

function ajax_freezedb(permanent_freeze, keyword_final, caching) {
    console.debug("load archives - with caching "+caching);
    var tbody_elem = $("#frozenarchivetable tbody");
    var pending_updates = false;
    var loading_msg = "Loading archives ...";
    /* Force caching to boolean if e.g. left out */
    if (!caching) {
        caching = false;
        loading_msg = "Updating archives - may take a while";
    }
    $("#ajax_status").addClass("spinner iconleftpad");
    $("#ajax_status").html(loading_msg);
    /* Request archive list in the background and handle as soon as
    results come in */
    $.ajax({
      url: "?output_format=json&operation=list&caching="+caching,
      type: "GET",
      dataType: "json",
      cache: false,
      success: function(jsonRes, textStatus) {
          console.debug("got response from list");
          var chunk_size = 200;
          var table_entries = "", error = "";
          var i, j;
          var arch, entry;
          //console.debug("empty table");
          $(tbody_elem).empty();
          /* Grab results from json response and insert items in table */
          for (i=0; i<jsonRes.length; i++) {
              //console.debug("looking for content: "+ jsonRes[i].object_type);
              if (jsonRes[i].object_type === "error_text") {
                  console.error("list: "+jsonRes[i].text);
                  error += jsonRes[i].text;
              } else if (jsonRes[i].object_type === "frozenarchives") {
                  if (caching) {
                      pending_updates = jsonRes[i].pending_updates;
                  }
                  var archives = jsonRes[i].frozenarchives;
                  for (j=0; j<archives.length; j++) {
                      arch = archives[j];
                      //console.info("found archive: "+arch.name);
                      var viewlink = "";
                      if (arch.viewfreezelink !== undefined) {
                          viewlink = format_link(arch.viewfreezelink);
                      }
                      var editlink = "";
                      if (arch.editfreezelink !== undefined) {
                          editlink = format_link(arch.editfreezelink);
                      }
                      var dellink = "";
                      var flavor = arch.flavor;
                      if (arch.state != keyword_final || permanent_freeze.indexOf(flavor) == -1) {
                          if (arch.delfreezelink !== undefined) {
                              dellink = format_link(arch.delfreezelink);
                          }
                      }
                      entry = "<tr>"+base_td(arch.id)+center_td(viewlink+
                                                                editlink+
                                                                dellink)+
                          base_td(arch.name)+base_td(arch.created)+
                          attr_td(arch.flavor, "class='flavor'")+base_td(arch.state)+
                          center_td(arch.frozenfiles)+"</tr>";
                      //console.debug("append entry: "+entry);
                      table_entries += entry;
                      /* chunked updates - append after after every chunk_size entries */
                      if (j > 0 && j % chunk_size === 0) {
                          console.debug('append chunk of ' + chunk_size + ' entries');
                          $(tbody_elem).append(table_entries);
                          table_entries = "";
                      }
                  }
              }
          }
          if (table_entries) {
              console.debug('append remaining chunk of ' + (j % chunk_size) + ' entries');
              $(tbody_elem).append(table_entries);
          }
          $("#ajax_status").removeClass("spinner iconleftpad");
          $("#ajax_status").empty();
          if (error) {
              $("#ajax_status").append("<span class=\'errortext\'>"+
                                       "Error: "+error+"</span>");
          } else if (pending_updates) {
              /* NOTE: pending archive update detected - background update */
              $("#ajax_status").append("<span class=\'infotext\'>"+
                                       "Loaded cached archives - update pending</span>");
              setTimeout(function() {
                  ajax_freezedb(permanent_freeze, keyword_final, false);
              }, 3000);
          }
          $("#frozenarchivetable").trigger("update");

      },
      error: function(jqXHR, textStatus, errorThrown) {
          handle_ajax_error(jqXHR, textStatus, errorThrown, "freezedb", "list",
                            "#ajax_status");
      }
  });
}

function ajax_showfreeze(freeze_id, flavor, checksum_list, keyword_updating,
                         keyword_final, freeze_doi_url, freeze_doi_url_field, caching, 
                         sorted_hash_algos) {
    console.debug("load archive "+freeze_id+" of flavor "+flavor+" with "+
                  checksum_list.toString()+" checksums with caching "+caching);
    var tbody_elem = $("#frozenfilestable tbody");
    var arch_tbody = $(".frozenarchivedetails tbody");
    var pending_updates = false;
    var loading_msg = "Loading archives ...";
    /* Force caching to boolean if e.g. left out */
    if (!caching) {
        caching = false;
        loading_msg = "Updating archives - may take a while";
    }
    $("#ajax_status").addClass("spinner iconleftpad");
    $("#ajax_status").html("Loading archive "+freeze_id+" ...");
    /* Request archive list in the background and handle as soon as
    results come in */
    $.ajax({
        url: "?freeze_id="+freeze_id+"&flavor="+flavor+"&checksum="+
            checksum_list.join("&checksum=")+"&output_format=json&operation=list&caching="+caching,
      type: "GET",
      dataType: "json",
      cache: false,
      success: function(jsonRes, textStatus) {
          console.debug("got response from list");
          var chunk_size = 200;
          var table_entries = "", error = "";
          var i, j;
          var arch, file, entry, publish_url = "";
          //console.debug("empty table");
          $(tbody_elem).empty();
          $(arch_tbody).empty();
          /* Grab results from json response and insert items in table */
          for (i=0; i<jsonRes.length; i++) {
              //console.debug("looking for content: "+ jsonRes[i].object_type);
              if (jsonRes[i].object_type === "error_text") {
                  console.error("list: "+jsonRes[i].text);
                  error += " "+jsonRes[i].text;
              } else if (jsonRes[i].object_type === "frozenarchive") {
                  if (caching) {
                      pending_updates = jsonRes[i].pending_updates;
                  }
                  //console.debug("found frozenarchive");
                  arch = jsonRes[i];
                  //console.debug("append details");
                  var published = "No";
                  if (arch.publish) {
                      publish_url = arch.publish_url;
                      published = "Yes ("+format_url(publish_url)+")";
                  }
                  var location = "";
                  if (arch.location !== undefined) {
                      var loc = arch.location;
                      for (j=0; j<loc.length; j++) {
                          location += "<tr>"+title_td("On "+loc[j][0])+
                              base_td(loc[j][1])+"</tr>";
                      }
                  }
                  entry = "<tr>"+title_td("ID")+base_td(arch.id)+"</tr><tr>"+
                      title_td("Name")+base_td(arch.name)+"</tr><tr>"+
                      title_td("Flavor")+base_td(arch.flavor)+"</tr>";
                  if (arch.flavor !== 'backup') {
                      entry += "<tr>"+title_td("Description")+
                      base_td("<pre class='archive-description'>"+arch.description+"</pre>")+
                      "</tr><tr>"+title_td("Published")+base_td(published)+"</tr>";
                  } else {
                      /* no op */
                  }
                  entry += "<tr>"+title_td("State")+base_td(arch.state)+
                      "</tr><tr>"+title_td("Creator")+base_td(arch.creator)+
                      "</tr><tr>"+title_td("Created")+base_td(arch.created)+
                      "</tr>"+location;
                  $(arch_tbody).append(entry);
                  var files = arch.frozenfiles;
                  var show_link, del_link, checksum_field;
                  for (j=0; j<files.length; j++) {
                      file = files[j];
                      //console.info("found file: "+file.name);
                      if (file.showfile_link !== undefined) {
                          //console.info("found showfile link: "+file.showfile_link);
                          show_link = format_link(file.showfile_link);
                      } else {
                          show_link = '';
                      }
                      if (file.delfile_link !== undefined) {
                          //console.info("found delfile link: "+file.delfile_link);
                          del_link = format_link(file.delfile_link);
                      } else {
                          del_link = '';
                      }
                      entry = "<tr>"+base_td(file.name)+
                          center_td(show_link+" "+del_link)+
                          center_td(file.date)+center_td(file.size);
                      $.each(sorted_hash_algos, function(algo_index, algo) {
                          //console.info("handling checksum algo: "+algo);
                          checksum_field = algo + 'sum';
                          //console.info("add file."+checksum_field);
                          entry += attr_td(file[checksum_field], "class='"+checksum_field+" monospace hidden'");
                      });
                      entry += "</tr>";
                      //console.debug("append entry: "+entry);
                      table_entries += entry;
                      /* chunked updates - append after after every chunk_size entries */
                      if (j > 0 && j % chunk_size === 0) {
                          console.debug('append chunk of ' + chunk_size + ' entries');
                          $(tbody_elem).append(table_entries);
                          table_entries = "";
                      }
                  }
              }
          }
          if (table_entries) {
              console.debug('append remaining chunk of ' + (j % chunk_size) + ' entries');
              $(tbody_elem).append(table_entries);
          }
          //console.debug("updated files table is: "+$(tbody_elem).html());
          //console.debug("updated details table is: "+$(arch_tbody).html());
          $("#ajax_status").removeClass("spinner iconleftpad");
          $("#ajax_status").empty();
          if (error) {
              $("#ajax_status").append("<span class=\'errortext\'>"+
                                       "Error: "+error+"</span>");
          } else if (pending_updates) {
              /* NOTE: pending archive update detected - background update */
              $("#ajax_status").append("<span class=\'infotext\'>"+
                                       "Loaded cached archive - update pending</span>");
              setTimeout(function() {
                  ajax_showfreeze(freeze_id, flavor, checksum_list, 
                                  keyword_updating, keyword_final, 
                                  freeze_doi_url, freeze_doi_url_field, false,
                                  sorted_hash_algos);
              }, 3000);
          }
          /* Make sure requested checksum columns are visible */
          console.debug("show checksums");
          for (var entry_no=0; entry_no < checksum_list.length; entry_no++) {
              $("."+checksum_list[entry_no]+"sum").show();
          }
          console.debug("show hidden divs if relevant");
          if (arch.state === keyword_updating) {
              console.debug("show update warning");
              $("div.updatearchive").show();
          } else if (arch.state !== keyword_final) {
              console.debug("show edit and finalize buttons");
              $("div.editarchive").show();
          } else if (arch.flavor !== 'backup' && freeze_doi_url && publish_url) {
              console.debug("show register DOI button");
              $("div.registerarchive").show();
              /* NOTE: we add the landing page URL both in the form field and
                 append it directly in the query string.
              */
              console.debug("changing publish_url from "+$("#registerfreeze"+freeze_doi_url_field+"field").val()+" to "+publish_url);
              $("#registerfreeze"+freeze_doi_url_field+"field").val(publish_url);
              console.debug("changed publish_url to "+$("#registerfreeze"+freeze_doi_url_field+"field").val());
              $("#registerfreezeform").attr('action', freeze_doi_url+'&'+freeze_doi_url_field+"="+publish_url);
              console.debug("changed action to "+$("#registerfreezeform").attr('action'));
          } else {
              console.info("not showing edit or register DOI");
          }
          $("#frozenfilestable").trigger("update");
      },
      error: function(jqXHR, textStatus, errorThrown) {
          handle_ajax_error(jqXHR, textStatus, errorThrown, "showfreeze", "list",
                            "#ajax_status");
      }
  });
}

function ajax_vgridman(vgrid_label, vgrid_links, caching) {
    console.debug("load vgrids - with caching "+caching);
    var tbody_elem = $("#vgridtable tbody");
    var pending_updates = false;
    var loading_msg = "Loading "+vgrid_label+"s ...";
    /* Force caching to boolean if e.g. left out */
    if (!caching) {
        caching = false;
        loading_msg = "Updating "+vgrid_label+"s - may take a while";
    }
    $("#ajax_status").addClass("spinner iconleftpad");
    $("#ajax_status").html(loading_msg);
    /* Request vgrid list in the background and handle as soon as
    results come in */
    $.ajax({
      url: "?output_format=json&operation=list&caching="+caching,
      type: "GET",
      dataType: "json",
      cache: false,
      success: function(jsonRes, textStatus) {
          console.debug("got response from list");
          //console.debug("empty table");
          $(tbody_elem).empty();
          var chunk_size = 200;
          var table_entries = "", error = "";
          var i, j, k;
          var vgrid, entry;
          /* Grab results from json response and insert items in table */
          for (i=0; i<jsonRes.length; i++) {
              //console.debug("looking for content: "+ jsonRes[i].object_type);
              if (jsonRes[i].object_type === "error_text") {
                  console.error("list: "+jsonRes[i].text);
                  error += jsonRes[i].text;
              } else if (jsonRes[i].object_type === "vgrid_list") {
                  if (caching) {
                      pending_updates = jsonRes[i].pending_updates;
                  }
                  var vgrids = jsonRes[i].vgrids;
                  for (j=0; j < vgrids.length; j++) {
                      vgrid = vgrids[j];
                      //console.info("found vgrid: "+vgrid.name);
                      var viewlink = format_link(vgrid.viewvgridlink);
                      var adminlink = "";
                      var memberlink = "";
                      var activelinks = "";
                      if (vgrid.administratelink !== undefined) {
                          adminlink = format_link(vgrid.administratelink);
                      }
                      if (vgrid.memberlink !== undefined) {
                          memberlink = format_link(vgrid.memberlink);
                      }
                      entry = "<tr>"+base_td(vgrid.name)+center_td(viewlink)+
                          center_td(adminlink)+center_td(memberlink);
                      /* Adhere to vgrid_links list content and order */
                      for (k=0; k<vgrid_links.length; k++) {
                          activelinks = "";
                          var linkname = vgrid_links[k];
                          if (linkname === "files") {
                              if (vgrid.sharedfolderlink !== undefined) {
                                  activelinks += format_link(vgrid.sharedfolderlink);
                              }
                          } else if (linkname === "web") {
                              if (vgrid.enterprivatelink !== undefined) {
                                  activelinks += format_link(vgrid.enterprivatelink);
                                  activelinks += " ";
                              }
                              if (vgrid.editprivatelink !== undefined) {
                                  activelinks += format_link(vgrid.editprivatelink);
                                  activelinks += " ";
                              }
                              if (vgrid.enterpubliclink !== undefined) {
                                  activelinks += format_link(vgrid.enterpubliclink);
                                  activelinks += " ";
                              }
                              if (vgrid.editpubliclink !== undefined) {
                                  activelinks += format_link(vgrid.editpubliclink);
                                  activelinks += " ";
                              }
                          } else if (linkname === "scm") {
                              if (vgrid.ownerscmlink !== undefined) {
                                  activelinks += format_link(vgrid.ownerscmlink);
                                  activelinks += " ";
                              }
                              if (vgrid.memberscmlink !== undefined) {
                                  activelinks += format_link(vgrid.memberscmlink);
                                  activelinks += " ";
                              }
                          } else if (linkname === "tracker") {
                              if (vgrid.ownertrackerlink !== undefined) {
                                  activelinks += format_link(vgrid.ownertrackerlink);
                                  activelinks += " ";
                              }
                              if (vgrid.membertrackerlink !== undefined) {
                                  activelinks += format_link(vgrid.membertrackerlink);
                                  activelinks += " ";
                              }
                          } else if (linkname === "forum") {
                              if (vgrid.privateforumlink !== undefined) {
                                  activelinks += format_link(vgrid.privateforumlink);
                                  activelinks += " ";
                              }
                              if (vgrid.publicforumlink !== undefined) {
                                  activelinks += format_link(vgrid.publicforumlink);
                                  activelinks += " ";
                              }
                          } else if (linkname === "workflows") {
                              if (vgrid.privateworkflowslink !== undefined) {
                                  activelinks += format_link(vgrid.privateworkflowslink);
                              }
                          } else if (linkname === "monitor") {
                              if (vgrid.privatemonitorlink !== undefined) {
                                  activelinks += format_link(vgrid.privatemonitorlink);
                              }
                          } else {
                              console.error("unknown vgrid link: "+linkname+
                                            " or missing vgrid item link!");
                          }
                          entry += center_td(activelinks);
                      }
                      entry += "</tr>";
                      //console.debug("append entry: "+entry);
                      table_entries += entry;
                      /* chunked updates - append after after every chunk_size entries */
                      if (j > 0 && j % chunk_size === 0) {
                          console.debug('append chunk of ' + chunk_size + ' entries');
                          $(tbody_elem).append(table_entries);
                          table_entries = "";
                      }
                  }
              }
          }
          if (table_entries) {
              console.debug('append remaining chunk of ' + (j % chunk_size) + ' entries');
              $(tbody_elem).append(table_entries);
          }
          $("#ajax_status").removeClass("spinner iconleftpad");
          $("#ajax_status").empty();
          if (error) {
              $("#ajax_status").append("<span class=\'errortext\'>"+
                                       "Error: "+error+"</span>");
          } else if (pending_updates) {
              /* NOTE: pending vgrid map update detected - background update */
              $("#ajax_status").append("<span class=\'infotext\'>"+
                                       "Loaded cached "+vgrid_label+
                                       "s - update pending</span>");
              setTimeout(function() {
                  ajax_vgridman(vgrid_label, vgrid_links, false);
              }, 3000);
          }
          $("#vgridtable").trigger("update");

      },
      error: function(jqXHR, textStatus, errorThrown) {
          handle_ajax_error(jqXHR, textStatus, errorThrown, "vgridman", "list",
                            "#ajax_status");
      }
  });
}

function ajax_resman(caching) {
    console.debug("load resources - with caching "+caching);
    var tbody_elem = $("#resourcetable tbody");
    var pending_updates = false;
    var loading_msg = "Loading resources ...";
    /* Force caching to boolean if e.g. left out */
    if (!caching) {
        caching = false;
        loading_msg = "Updating resources - may take a while";
    }
    $("#ajax_status").addClass("spinner iconleftpad");
    $("#ajax_status").html(loading_msg);
    /* Request resource list in the background and handle as soon as
    results come in */
    $.ajax({
      url: "?output_format=json&operation=list&caching="+caching,
      type: "GET",
      dataType: "json",
      cache: false,
      success: function(jsonRes, textStatus) {
          console.debug("got response from list");
          //console.debug("empty table");
          $(tbody_elem).empty();
          var chunk_size = 200;
          var table_entries = "", error = "";
          var i, j, k;
          var resource, res_type, res_hint, rte_hint, entry;
          /* Grab results from json response and insert items in table */
          for (i=0; i<jsonRes.length; i++) {
              //console.debug("looking for content: "+ jsonRes[i].object_type);
              if (jsonRes[i].object_type === "error_text") {
                  console.error("list: "+jsonRes[i].text);
                  error += jsonRes[i].text;
              } else if (jsonRes[i].object_type === "resource_list") {
                  if (caching) {
                      pending_updates = jsonRes[i].pending_updates;
                  }
                  var resources = jsonRes[i].resources;
                  for (j=0; j<resources.length; j++) {
                      resource = resources[j];
                      //console.info("found resource: "+resource.name);
                      var detailslink = "";
                      var ownerlink = "";
                      if (resource.resdetailslink !== undefined) {
                          detailslink = format_link(resource.resdetailslink);
                      }
                      if (resource.resownerlink !== undefined) {
                          ownerlink = format_link(resource.resownerlink);
                      }
                      res_type = "real";
                      if (resource.SANDBOX) {
                          res_type = 'sandbox';
                      }
                      res_hint = 'class="'+res_type+'res iconspace iconleftpad" title="'+res_type+
                          ' resource"';
                      rte_hint = center_class+' title="'+
                          resource.RUNTIMEENVIRONMENT.toString()+'"';
                      entry = "<tr>"+attr_td(resource.name, res_hint)+
                          center_td(detailslink)+center_td(ownerlink)+
                          attr_td(resource.RUNTIMEENVIRONMENT.length, rte_hint)+
                          center_td(resource.PUBLICNAME)+
                          center_td(resource.NODECOUNT)+
                          center_td(resource.CPUCOUNT)+
                          center_td(resource.MEMORY)+center_td(resource.DISK)+
                          center_td(resource.ARCHITECTURE)+"</tr>";
                      //console.debug("append entry: "+entry);
                      table_entries += entry;
                      /* chunked updates - append after after every chunk_size entries */
                      if (j > 0 && j % chunk_size === 0) {
                          console.debug('append chunk of ' + chunk_size + ' entries');
                          $(tbody_elem).append(table_entries);
                          table_entries = "";
                      }
                  }
              }
          }
          if (table_entries) {
              console.debug('append remaining chunk of ' + (j % chunk_size) + ' entries');
              $(tbody_elem).append(table_entries);
          }
          $("#ajax_status").removeClass("spinner iconleftpad");
          $("#ajax_status").empty();
          if (error) {
              $("#ajax_status").append("<span class=\'errortext\'>"+
                                       "Error: "+error+"</span>");
          } else if (pending_updates) {
              /* NOTE: pending resource map update detected - background update */
              $("#ajax_status").append("<span class=\'infotext\'>"+
                                       "Loaded cached resources - update pending</span>");
              setTimeout(function() {
                  ajax_resman(false);
              }, 3000);
          }
          $("#resourcetable").trigger("update");

      },
      error: function(jqXHR, textStatus, errorThrown) {
          handle_ajax_error(jqXHR, textStatus, errorThrown, "resman", "list",
                            "#ajax_status");
      }
  });
}

function ajax_people(protocols, caching) {
    console.debug("load users - with caching "+caching);
    var tbody_elem = $("#usertable tbody");
    var pending_updates = false;
    var loading_msg = "Loading users ...";
    /* Force caching to boolean if e.g. left out */
    if (!caching) {
        caching = false;
        loading_msg = "Updating users - may take a while";
    }
    $("#ajax_status").addClass("spinner iconleftpad");
    $("#ajax_status").html(loading_msg);
    /* Request user list in the background and handle as soon as
    results come in */
    $.ajax({
      url: "?output_format=json&operation=list&caching="+caching,
      type: "GET",
      dataType: "json",
      cache: false,
      success: function(jsonRes, textStatus) {
          console.debug("got response from list");
          //console.debug("empty table");
          $(tbody_elem).empty();
          var chunk_size = 200;
          var table_entries = "", error = "";
          var i, j, k;
          var usr, link_name, proto, entry;
          /* Grab results from json response and insert items in table */
          for (i=0; i<jsonRes.length; i++) {
              //console.debug("looking for content: "+ jsonRes[i].object_type);
              if (jsonRes[i].object_type === "error_text") {
                  console.error("list: "+jsonRes[i].text);
                  error += jsonRes[i].text;
              } else if (jsonRes[i].object_type === "user_list") {
                  if (caching) {
                      pending_updates = jsonRes[i].pending_updates;
                  }
                  var users = jsonRes[i].users;
                  for (j=0; j<users.length; j++) {
                      usr = users[j];
                      //console.info("found user: "+usr.name);
                      var viewlink = format_link(usr.userdetailslink);
                      var sendlink = "";
                      var img_html = '';
                      if (usr.avatar_url) {
                          img_html = '<img alt="avatar" class="profile-thumb" src="'+usr.avatar_url+'">';
                      }
                      entry = "<tr>"+base_td(img_html)+base_td(usr.pretty_id)+center_td(viewlink);
                      for (k=0; k<protocols.length; k++) {
                          proto = protocols[k];
                          link_name = "send"+proto+"link";
                          sendlink = "---";
                          if (usr[link_name] !== undefined) {
                              sendlink = format_link(usr["send"+proto+"link"]);
                          }
                          entry += center_td(sendlink);
                      }
                      entry += "</tr>";
                      //console.debug("append entry: "+entry);
                      table_entries += entry;
                      /* chunked updates - append after after every chunk_size entries */
                      if (j > 0 && j % chunk_size === 0) {
                          console.debug('append chunk of ' + chunk_size + ' entries');
                          $(tbody_elem).append(table_entries);
                          table_entries = "";
                      }
                  }
              }
          }
          if (table_entries) {
              console.debug('append remaining chunk of ' + (j % chunk_size) + ' entries');
              $(tbody_elem).append(table_entries);
          }
          $("#ajax_status").removeClass("spinner iconleftpad");
          $("#ajax_status").empty();
          if (error) {
              $("#ajax_status").append("<span class=\'errortext\'>"+
                                       "Error: "+error+"</span>");
          } else if (pending_updates) {
              /* NOTE: pending vgrid map update detected - background update */
              $("#ajax_status").append("<span class=\'infotext\'>"+
                                       "Loaded cached users - update pending</span>");
              setTimeout(function() {
                  ajax_people(protocols, false);
              }, 3000);
          }
          $("#usertable").trigger("update");

      },
      error: function(jqXHR, textStatus, errorThrown) {
          handle_ajax_error(jqXHR, textStatus, errorThrown, "people", "list",
                            "#ajax_status");
      }
  });
}

function ajax_workflowjobs(vgrid_name, flags) {
    console.debug("load workflow jobs and log");
    var tbody_elem = $("#workflowstable tbody");
    var logarea_elem = $("#logarea");
    //console.debug("empty table");
    $(tbody_elem).empty();
    $(logarea_elem).empty();
    $("#ajax_status").addClass("spinner iconleftpad");
    $("#ajax_status").html("Loading workflow jobs and log ...");
    /* Request workflow jobs and log in the background and handle as soon as
    results come in */
    $.ajax({
        url: "?output_format=json&operation=list&vgrid_name="+vgrid_name+"&flags="+flags,
      type: "GET",
      dataType: "json",
      cache: false,
      success: function(jsonRes, textStatus) {
          console.debug("got response from list");
          var chunk_size = 200;
          var table_entries = "", error = "";
          var i, j;
          var job, entry;
          /* Grab results from json response and insert items in table */
          for (i=0; i<jsonRes.length; i++) {
              console.debug("looking for content: "+ jsonRes[i].object_type);
              if (jsonRes[i].object_type === "error_text") {
                  console.error("list: "+jsonRes[i].text);
                  error += jsonRes[i].text;
              } else if (jsonRes[i].object_type === "trigger_job_list") {
                  var workflowjobs = jsonRes[i].trigger_jobs;
                  for (j=0; j<workflowjobs.length; j++) {
                      job = workflowjobs[j];
                      //console.info("found job: "+job.job_id);
                      entry = "<tr>"+base_td(job.job_id)+base_td(job.rule_id)+
                          base_td(job.path)+base_td(job.action)+
                          base_td(job.time)+base_td(job.status)+
                          "</tr>";
                      console.debug("append entry: "+entry);
                      table_entries += entry;
                      /* chunked updates - append after after every chunk_size entries */
                      if (j > 0 && j % chunk_size === 0) {
                          console.debug('append chunk of ' + chunk_size + ' entries');
                          $(tbody_elem).append(table_entries);
                          table_entries = "";
                      }
                  }
              } else if (jsonRes[i].object_type === "trigger_log") {
                  var log_content = jsonRes[i].log_content;
                  console.debug("append log: "+log_content);
                  $(logarea_elem).append(log_content);
                  $(logarea_elem).scrollTop($(logarea_elem)[0].scrollHeight);
              }
          }
          if (table_entries) {
              console.debug('append remaining chunk of ' + (j % chunk_size) + ' entries');
              $(tbody_elem).append(table_entries);
          }
          $("#ajax_status").removeClass("spinner iconleftpad");
          $("#ajax_status").empty();
          if (error) {
              $("#ajax_status").append("<span class=\'errortext\'>"+
                                       "Error: "+error+"</span>");
          }
          $("#workflowstable").trigger("update");

      },
      error: function(jqXHR, textStatus, errorThrown) {
          handle_ajax_error(jqXHR, textStatus, errorThrown, "workflowjobs", "list",
                            "#ajax_status");
      }
  });
}

function ajax_gdp_project_info(callback, project_name) {
    console.debug("ajax_gdp_project_info: " + project_name);
    var result = { OK: [], WARNING: [], ERROR: [] };
    var target_op = "gdpman";
    console.info("Lookup CSRF token for " + target_op);

    var jsonSettings = {
        base_vgrid_name: project_name,
        output_format: "json",
        action: "project_info"
    };
    if (csrf_map[target_op] !== undefined) {
        jsonSettings[csrf_field] = csrf_map[target_op];
        console.info("Found CSRF token " + jsonSettings["_csrf"]);
    } else {
        console.info("No CSRF token for " + target_op);
    }

    $.ajax({
        url: target_op + ".py",
        data: jsonSettings,
        type: "POST",
        dataType: "json",
        cache: false,
        success: function(jsonRes) {
            for (var i = 0; i < jsonRes.length; i++) {
                //console.debug("jsonRes: " + JSON.stringify(jsonRes[i]));
                if (jsonRes[i].object_type === "project_info") {
                    console.debug("ajax_gdp_project_info: " +
                      JSON.stringify(jsonRes[i].info));
                    result.OK.push(jsonRes[i].info);
                } else if (jsonRes[i]["object_type"] === "warning") {
                    console.warning(
                        "ajax_gdp_project_info: " + jsonRes[i].text
                    );
                    result.WARNING.push(jsonRes[i].text);
                } else if (jsonRes[i]["object_type"] === "error_text") {
                    console.error("ajax_gdp_project_info: " + jsonRes[i].text);
                    result.ERROR.push(jsonRes[i].text);
                }
            }
            callback(project_name, result);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error(
                "ajax_gdp_project_info: " +
                    "status: " +
                    textStatus +
                    "error: " +
                    errorThrown
            );
            result.ERROR.push(textStatus);
            result.ERROR.push(errorThrown);
            callback(project_name, result);
        }
    });
}

/* OpenID availability checker for use on signup and login pages */
function check_oid_available(action, oid_title, oid_url, tag_prefix) {
    $("#"+tag_prefix+"status").removeClass();
    $("#"+tag_prefix+"status").addClass("status_box");
    $("#"+tag_prefix+"status").addClass("spinner iconleftpad");
    $("#"+tag_prefix+"status").append("<span>"+oid_title+" OpenID server status: </span>");
    $("#"+tag_prefix+"status").append("<span id="+tag_prefix+"msg></span> <span id="+tag_prefix+"err></span>");
    $("#"+tag_prefix+"msg").append("checking availability ...");
    /* Run oidping check in the background and handle as soon as results come in */
    $.ajax({
        url: "oidping.py?output_format=json&url="+oid_url,
        type: "GET",
        dataType: "json",
        cache: false,
        success: function(jsonRes, textStatus) {
            var i = 0;
            var online = false;
            var err = "";
            // Grab results from json response and place them in resource status.
            for (i=0; i<jsonRes.length; i++) {
                //alert("debug: parsing entry "+i);
                //alert("debug: parsing "+jsonRes[i]);
                //$("#"+tag_prefix+"debug").append(jsonRes[i].toSource());
                if (jsonRes[i].object_type === "openid_status") {
                    online = jsonRes[i].status;
                    err = jsonRes[i].error;
                    $("#"+tag_prefix+"status").removeClass("spinner iconleftpad");
                    $("#"+tag_prefix+"msg").empty();
                    $("#"+tag_prefix+"msg").append(online);
                    if (online === "online") {
                        $("#"+tag_prefix+"status").addClass("ok iconleftpad");
                        $("#"+tag_prefix+"msg").addClass("status_online");
                        $("#"+tag_prefix+"button").attr("disabled", false);
                    } else {
                        $("#"+tag_prefix+"err").append("("+err+")<br/>");
                        $("#"+tag_prefix+"status").append("<span>Unable to "+action+" with this method until OpenID server comes back online. Please report the problem to the "+oid_title+" OpenID administrators.</span>");
                        $("#"+tag_prefix+"status").addClass("error iconleftpad");
                        $("#"+tag_prefix+"msg").addClass("status_offline");
                        $("#"+tag_prefix+"button").attr("disabled", true);
                    }
                    break;
                }
            }
        }
    });
}

/* Seafile settings helper used to switch between register and save sections */
function select_seafile_section(section_prefix) {
    var reg_prefix="seafilereg";
    var save_prefix="seafilesave";
    if (section_prefix === reg_prefix) {
        //alert("show reg section");
        $("#"+reg_prefix+"access").show();
        $("#"+save_prefix+"access").hide();
    } else if (section_prefix === save_prefix) {
        //alert("show save section");
        $("#"+reg_prefix+"access").hide();
        $("#"+save_prefix+"access").show();
    } else {
        alert("invalid section prefix: "+section_prefix);
        return false;
    }
    return true;
}
/* Seafile registration helper to get the CSRF tag from the signup form and
   switch to the save form if registration url shows that user registered and
   logged in already */
function prepare_seafile_settings(reg_url, username, integration,
                                  status_prefix, reg_prefix, save_prefix) {
    $("#"+reg_prefix+"button").attr("disabled", false);
    $("#"+save_prefix+"button").attr("disabled", false);
    $("#"+status_prefix+"status").removeClass();
    $("#"+status_prefix+"status").addClass("status_box");
    $("#"+status_prefix+"status").addClass("spinner iconleftpad");
    $("#"+status_prefix+"status").append("<span>Seafile server status: </span>");
    $("#"+status_prefix+"status").append("<span id="+status_prefix+"msg></span>");
    $("#"+status_prefix+"msg").append("checking availability ...");
    /* Run CSRF tag grabber in the background and handle as soon as results come in */
    //console.log("DEBUG: run csrf token grabber: "+reg_url);
    $.ajax({
        url: reg_url,
        dataType: "html",
        cache: false,
        /* NOTE: register will not work unless we pass the csrfmiddlewaretoken
                 AND provide the proper sfcrsftoken cookie!
                 The cookie is passed by using withCredentials and it requires
                 the seafile server to be local or use CORS.
                 More details about setting it up at
                 http://promincproductions.com/blog/cross-domain-ajax-request-cookies-cors/#How-to-Pass-Cookies-on-a-Cross-Domain-AJAX-Request-from-Browser-to-Server
         */
        xhrFields: { withCredentials: true },
        success: function(output, status, xhr) {
            /* Parse output for hidden form input with csrf token */
            //console.log("DEBUG: got csrf output: "+output);
            //alert("DEBUG: got csrf status: "+status);
            $("#"+status_prefix+"msg").empty();
            $("#"+status_prefix+"status").removeClass("spinner iconleftpad");
            var csrf_token = $("input[name=csrfmiddlewaretoken]", output).val();
            /* NOTE: until Seafile 7.x the sign-up page contained the username
               of any logged in user, but from 7.x we can only rely on a more
               indirect indication that a user is logged in. 
            */
            var id_user = $("#account", output).find("div.txt:contains("+username+")").text();
            var account_name = $("#account", output).find("div.txt").text();
            var signed_in_msg = $("#main .login-panel", output).find("p").text();
            var signed_in = signed_in_msg.includes("already signed in");
            var logged_in = "";
            $("#"+status_prefix+"msg").append('online');
            if (id_user || account_name || signed_in) {
                logged_in = "you are already registered and logged in as "+username;
                //alert("DEBUG: "+logged_in+" ("+id_user+")");
                // Try to avoid confusion if user is already registered
                $("#"+reg_prefix+"button").attr("disabled", true);
                $("#"+status_prefix+"status").addClass("ok iconleftpad");
                $("#"+status_prefix+"msg").addClass("status_online");
                select_seafile_section(save_prefix);
            } else if (csrf_token !== undefined) {
                //console.log("DEBUG: got csrf token: "+csrf_token);
                if (integration) {
                    logged_in = "apparently you already registered and integrated as "+username;
                    // Try to avoid confusion if user already registered
                    $("#"+reg_prefix+"button").attr("disabled", true);
                    select_seafile_section(save_prefix);
                } else {
                    logged_in = "your are either not registered yet or not currently logged in";
                    select_seafile_section(reg_prefix);
                }
                //alert("DEBUG: "+logged_in+" ("+id_user+")");
                $("#"+status_prefix+"status").addClass("ok iconleftpad");
                $("#"+status_prefix+"msg").addClass("status_online");
                $("input[name=csrfmiddlewaretoken]").val(csrf_token);
                //console.log("cookies: "+document.cookie);
            } else {
                console.error("unknown seafile state: id "+id_user+" account "+
                              account_name+" signed_in "+signed_in);
                //alert("Warning: unknown state");
                logged_in = "unexpected response from server";
                $("#"+status_prefix+"status").addClass("warn iconleftpad");
                $("#"+status_prefix+"msg").addClass("status_slack");
            }
            $("#"+status_prefix+"status").append(" <span>("+logged_in+")</span>");

        },
        error: function(xhr, status, error) {
            //console.log("ERROR: ajax failed! server probably unavailable");
            $("#"+status_prefix+"msg").empty();
            $("#"+status_prefix+"msg").append('offline');
            $("#"+status_prefix+"status").append(" <span>(Error: "+error+")</span>");
            $("#"+status_prefix+"status").addClass("error iconleftpad");
            $("#"+status_prefix+"msg").addClass("status_offline");
            select_seafile_section(save_prefix);
        }
    });
}
