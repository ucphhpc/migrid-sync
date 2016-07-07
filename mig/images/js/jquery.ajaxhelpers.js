/*

  #
  # --- BEGIN_HEADER ---
  #
  # jquery.ajaxhelpers - jquery based ajax helpers for managers
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

  # This is a modified version of the Matlab Grid service by Jost Berthold.
  # Original license headers follow below.

*/

function format_url(url) {
    return '<a class="link" href="'+url+'">'+url+'</a>';
}

function format_link(link_item) {
    var link = '<a ';
    if (link_item.id != undefined) {
        link += 'id="'+link_item.id+'" ';
    }
    if (link_item.class != undefined) {
        link += 'class="'+link_item.class+'" ';
    }
    if (link_item.title != undefined) {
        link += 'title="'+link_item.title+'" ';
    }
    if (link_item.target != undefined) {
        link += 'target="'+link_item.target+'" ';
    }
    link += 'href="'+link_item.destination+'">';
    if (link_item.text != undefined) {
        link += link_item.text;
    }
    link += '</a>';
    return link
}

function ajax_redb(_freeze) {
    console.debug("load runtime envs");
    $("#load_status").addClass("spinner iconleftpad");
    $("#load_status").html("Loading runtime envs ...");
    /* Request runtime envs list in the background and handle as soon as
    results come in */
    $.ajax({
      url: "?output_format=json;operation=list",
      type: "GET",
      dataType: "json",
      cache: false,
      success: function(jsonRes, textStatus) {
          console.debug("got response from list");
          var i = 0, j = 0;
          var rte, entry, error = "";
          //console.debug("empty table");
          $("#runtimeenvtable tbody").empty();
          /*
              Grab results from json response and insert rte items in table
              and append POST helpers to body to make confirm dialog work.
          */
          for (i=0; i<jsonRes.length; i++) {
              //console.debug("looking for content: "+ jsonRes[i].object_type);
              if (jsonRes[i].object_type == "error_text") {
                  console.error("list: "+jsonRes[i].text);
                  error += jsonRes[i].text;
              } else if (jsonRes[i].object_type == "html_form") {
                  entry = jsonRes[i].text;
                  if (entry.match(/function delete[0-9]+/)) {
                      //console.debug("append delete helper: "+entry);
                      $("body").append(entry);
                  }
              } else if (jsonRes[i].object_type == "runtimeenvironments") {
                  var runtimeenvs = jsonRes[i].runtimeenvironments;
                  var j = 0;
                  for (j=0; j<runtimeenvs.length; j++) {
                      rte = runtimeenvs[j];
                      //console.info("found runtimeenv: "+rte.name);
                      var viewlink = format_link(rte.viewruntimeenvlink);
                      var dellink = "";
                      if(rte.ownerlink != undefined) {
                          dellink = format_link(rte.ownerlink);
                      }
                      entry = "<tr><td>"+rte.name+"</td><td>"+viewlink+
                          "</td><td>"+dellink+"</td><td>"+rte.description+
                          "</td><td>"+rte.resource_count+"</td><td>"+
                          rte.created+"</td><td></tr>";
                      console.debug("append entry: "+entry);
                      $("#runtimeenvtable tbody").append(entry);
                  }
              }
          }
          $("#load_status").removeClass("spinner iconleftpad");
          $("#load_status").empty();
          if (error) {
              $("#load_status").append("<span class=\'errortext\'>"+
                                       "Error: "+error+"</span>");
          }
          $("#runtimeenvtable").trigger("update");

      },
      error: function(jqXHR, textStatus, errorThrown) {
          console.error("list failed: "+errorThrown);
          $("#load_status").removeClass("spinner iconleftpad");
          $("#load_status").empty();
          $("#load_status").append("<span class=\'errortext\'>"+
                                   "Error: "+errorThrown+"</span>");
      }
  });
}

function ajax_freezedb(permanent_freeze) {
    console.debug("load archives");
    $("#load_status").addClass("spinner iconleftpad");
    $("#load_status").html("Loading archives ...");
    /* Request archive list in the background and handle as soon as
    results come in */
    $.ajax({
      url: "?output_format=json;operation=list",
      type: "GET",
      dataType: "json",
      cache: false,
      success: function(jsonRes, textStatus) {
          console.debug("got response from list");
          var i = 0, j = 0;
          var arch, entry, error = "";
          //console.debug("empty table");
          $("#frozenarchivetable tbody").empty();
          /*
              Grab results from json response and insert archive items in table
              and append POST helpers to body to make confirm dialog work.
          */
          for (i=0; i<jsonRes.length; i++) {
              //console.debug("looking for content: "+ jsonRes[i].object_type);
              if (jsonRes[i].object_type == "error_text") {
                  console.error("list: "+jsonRes[i].text);
                  error += jsonRes[i].text;
              } else if (jsonRes[i].object_type == "html_form") {
                  entry = jsonRes[i].text;
                  if (entry.match(/function delete[0-9]+/)) {
                      //console.debug("append delete helper: "+entry);
                      $("body").append(entry);
                  }
              } else if (jsonRes[i].object_type == "frozenarchives") {
                  var archives = jsonRes[i].frozenarchives;
                  var j = 0;
                  for (j=0; j<archives.length; j++) {
                      arch = archives[j];
                      //console.info("found archive: "+arch.name);
                      var viewlink = format_link(arch.viewfreezelink);
                      var dellink = "";
                      if(!permanent_freeze) {
                          dellink = "<td>"+format_link(arch.delfreezelink)+"</td>";
                      }
                      entry = "<tr><td>"+arch.id+"</td><td>"+viewlink+
                              "</td><td>"+arch.name+"</td><td>"+
                              arch.created+"</td><td>"+
                              arch.frozenfiles+"</td>"+dellink+
                              "</tr>";
                      //console.debug("append entry: "+entry);
                      $("#frozenarchivetable tbody").append(entry);
                  }
              }
          }
          $("#load_status").removeClass("spinner iconleftpad");
          $("#load_status").empty();
          if (error) {
              $("#load_status").append("<span class=\'errortext\'>"+
                                       "Error: "+error+"</span>");
          }
          $("#frozenarchivetable").trigger("update");

      },
      error: function(jqXHR, textStatus, errorThrown) {
          console.error("list failed: "+errorThrown);
          $("#load_status").removeClass("spinner iconleftpad");
          $("#load_status").empty();
          $("#load_status").append("<span class=\'errortext\'>"+
                                   "Error: "+errorThrown+"</span>");
      }
  });
}

function ajax_showfreeze(freeze_id, checksum) {
    console.debug("load archive "+freeze_id+" with "+checksum+" checksum");
    $("#load_status").addClass("spinner iconleftpad");
    $("#load_status").html("Loading archive "+freeze_id+" ...");
    /* Request archive list in the background and handle as soon as
    results come in */
    $.ajax({
      url: "?freeze_id="+freeze_id+";checksum="+checksum+
           ";output_format=json;operation=list",
      type: "GET",
      dataType: "json",
      cache: false,
      success: function(jsonRes, textStatus) {
          console.debug("got response from list");
          var i = 0, j = 0;
          var arch, entry, error = "";
          //console.debug("empty table");
          $("#frozenfilestable tbody").empty();
          $(".frozenarchivedetails tbody").empty();
          /*
              Grab results from json response and insert archive items in table
              and append POST helpers to body to make confirm dialog work.
          */
          for (i=0; i<jsonRes.length; i++) {
              //console.debug("looking for content: "+ jsonRes[i].object_type);
              if (jsonRes[i].object_type == "error_text") {
                  console.error("list: "+jsonRes[i].text);
                  error += " "+jsonRes[i].text;
              } else if (jsonRes[i].object_type == "frozenarchive") {
                  //console.debug("found frozenarchive");
                  var arch = jsonRes[i];
                  //console.debug("append details");
                  var published = "No";
                  if (arch.publish) {
                      published = "Yes ("+format_url(arch.publish_url)+")";
                  }
                  var location = "";
                  if (arch.location != undefined) {
                      var loc = arch.location;
                      for (j=0; j<loc.length; j++) {
                          location += "<tr><td class=\'title\'>On "+
                          loc[j][0]+"</td><td>"+loc[j][1]+"</td></tr>";
                      }
                  }
                  entry = "<tr><td class=\'title\'>ID</td><td>"+arch.id+
                  "</td></tr><tr><td class=\'title\'>Name</td><td>"+arch.name+
                  "</td></tr><tr><td class=\'title\'>Description</td><td>"+
                  arch.description+"</td></tr><tr><td class=\'title\'>Published</td><td>"+published+
                  "</td></tr><tr><td class=\'title\'>Creator</td><td>"+arch.creator+
                  "</td></tr>"+location;                           
                  $(".frozenarchivedetails tbody").append(entry);
                  var files = arch.frozenfiles;
                  var j = 0;
                  for (j=0; j<files.length; j++) {
                      file = files[j];
                      //console.info("found file: "+file.name);
                      entry = "<tr><td>"+file.name+"</td><td>"+
                              file.size+"</td><td>"+
                              file.md5sum+"</td></tr>";
                      //console.debug("append entry: "+entry);
                      $("#frozenfilestable tbody").append(entry);
                  }
              }
          }
          //console.debug("updated files table is: "+$("#frozenfilestable tbody").html());
          //console.debug("updated details table is: "+$(".frozenarchivedetails tbody").html());
          $("#load_status").removeClass("spinner iconleftpad");
          $("#load_status").empty();
          if (error) {
              $("#load_status").append("<span class=\'errortext\'>"+
                                       "Error: "+error+"</span>");
          }
          $("#frozenfilestable").trigger("update");
      },
      error: function(jqXHR, textStatus, errorThrown) {
          console.error("list failed: "+errorThrown);
          $("#load_status").removeClass("spinner iconleftpad");
          $("#load_status").empty();
          $("#load_status").append("<span class=\'errortext\'>"+
                                   "Error: "+errorThrown+"</span>");
      }
  });
}

function ajax_vgridman(vgrid_label, vgrid_links) {
    console.debug("load vgrids");
    $("#load_status").addClass("spinner iconleftpad");
    $("#load_status").html("Loading "+vgrid_label+"s ...");
    /* Request vgrid list in the background and handle as soon as
    results come in */
    $.ajax({
      url: "?output_format=json;operation=list",
      type: "GET",
      dataType: "json",
      cache: false,
      success: function(jsonRes, textStatus) {
          console.debug("got response from list");
          var i, j, k;
          var vgrid, entry, error = "";
          //console.debug("empty table");
          $("#vgridtable tbody").empty();
          /*
              Grab results from json response and insert vgrid items in table
              and append POST helpers to body to make confirm dialog work.
          */
          for (i=0; i<jsonRes.length; i++) {
              //console.debug("looking for content: "+ jsonRes[i].object_type);
              if (jsonRes[i].object_type == "error_text") {
                  console.error("list: "+jsonRes[i].text);
                  error += jsonRes[i].text;
              } else if (jsonRes[i].object_type == "html_form") {
                  entry = jsonRes[i].text;
                  if (entry.match(/function (rm|req)vgrid(owner|member)[0-9]+/)) {
                      console.debug("append POST helper: "+entry);
                      $("body").append(entry);
                  }
              } else if (jsonRes[i].object_type == "vgrid_list") {
                  var vgrids = jsonRes[i].vgrids;
                  for (j=0; j<vgrids.length; j++) {
                      vgrid = vgrids[j];
                      //console.info("found vgrid: "+vgrid.name);
                      var viewlink = format_link(vgrid.viewvgridlink);
                      var adminlink = "";
                      var memberlink = "";
                      var activelinks = "";
                      if(vgrid.administratelink != undefined) {
                          adminlink = format_link(vgrid.administratelink);
                      }
                      if(vgrid.memberlink != undefined) {
                          memberlink = format_link(vgrid.memberlink);
                      }
                      var center="class='centertext'";
                      entry = "<tr><td>"+vgrid.name+"</td><td "+center+">"+
                          viewlink+"</td><td "+center+">"+adminlink+
                          "</td><td "+center+">"+memberlink+"</td>";
                      /* Adhere to vgrid_links list content and order */
                      for (k=0; k<vgrid_links.length; k++) {
                          activelinks = "";
                          var linkname = vgrid_links[k];
                          if (linkname == "files") {
                              if  (vgrid.sharedfolderlink != undefined) {
                                  activelinks = format_link(vgrid.sharedfolderlink);
                              }
                          } else if (linkname == "web") {
                              if(vgrid.enterprivatelink != undefined) {
                                  activelinks += format_link(vgrid.enterprivatelink);
                              }
                              if(vgrid.editprivatelink != undefined) {
                                  activelinks += format_link(vgrid.editprivatelink);
                              }
                              if(vgrid.enterpubliclink != undefined) {
                                  activelinks += format_link(vgrid.enterpubliclink);
                              }
                              if(vgrid.editpubliclink != undefined) {
                                  activelinks += format_link(vgrid.editpubliclink);
                              }
                          } else if (linkname == "scm") {
                              if(vgrid.ownerscmlink != undefined) {
                                  activelinks += format_link(vgrid.ownerscmlink);
                              }
                              if(vgrid.memberscmlink != undefined) {
                                  activelinks += format_link(vgrid.memberscmlink);
                              }
                          } else if (linkname == "tracker") {
                              if(vgrid.ownertrackerlink != undefined) {
                                  activelinks = format_link(vgrid.ownertrackerlink);
                              }
                              if(vgrid.membertrackerlink != undefined) {
                                  activelinks = format_link(vgrid.membertrackerlink);
                              }
                          } else if (linkname == "forum") {
                              if(vgrid.privateforumlink != undefined) {
                                  activelinks = format_link(vgrid.privateforumlink);
                              }
                              if(vgrid.publicforumlink != undefined) {
                                  activelinks = format_link(vgrid.publicforumlink);
                              }
                          } else if (linkname == "workflows") {
                              if(vgrid.privateworkflowslink != undefined) {
                                  activelinks = format_link(vgrid.privateworkflowslink);
                              }
                          } else if (linkname == "monitor") {
                              if(vgrid.privatemonitorlink != undefined) {
                                  activelinks = format_link(vgrid.privatemonitorlink);
                              }
                          } else {
                              console.error("unknown vgrid link: "+linkname+
                                            " or missing vgrid item link!");
                          }
                          entry += "<td "+center+">"+activelinks+"</td>";
                      }
                      entry += "</tr>";
                      console.debug("append entry: "+entry);
                      $("#vgridtable tbody").append(entry);
                  }
              }
          }
          $("#load_status").removeClass("spinner iconleftpad");
          $("#load_status").empty();
          if (error) {
              $("#load_status").append("<span class=\'errortext\'>"+
                                       "Error: "+error+"</span>");
          }
          $("#vgridtable").trigger("update");

      },
      error: function(jqXHR, textStatus, errorThrown) {
          console.error("list failed: "+errorThrown);
          $("#load_status").removeClass("spinner iconleftpad");
          $("#load_status").empty();
          $("#load_status").append("<span class=\'errortext\'>"+
                                   "Error: "+errorThrown+"</span>");
      }
  });
}

