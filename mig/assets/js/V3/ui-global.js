/*

#
# --- BEGIN_HEADER ---
#
# ui-global - UI V3 specific but skin-independent core functions
# Copyright (C) 2003-2019  The MiG Project lead by Brian Vinter
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

//TOGGLE BY ID - BOTTOM MENU ITEMS
function toggle_info(id) {
  var e = document.getElementById(id);
  var i = document.getElementById('supportInfo');
  var a = document.getElementById('aboutInfo');
  var b = document.getElementById('modern-ui-body');
  
  if(e.className == 'infoArea-container infoArea__active') {
    e.className =  'infoArea-container';
    b.style.overflow = 'auto';
  }
  else {
    e.className =  'infoArea-container infoArea__active';
    b.style.overflow = 'hidden';
    
    if (e.id == 'supportInfo') {
      a.className =  'infoArea-container';
    }
    if (e.id == 'aboutInfo') {
      i.className =  'infoArea-container';
    }
    else {
    }
  }        
}

$(document).mouseup(function (e)
{
  var container = $("#supportInfo"); // YOUR CONTAINER SELECTOR
  var container2 = $("#supportInfoButton");
  var x = document.getElementById("supportInfo");

  var container3 = $("#aboutInfo"); // YOUR CONTAINER SELECTOR
  var container4 = $("#aboutInfoButton");
  var y = document.getElementById("aboutInfo");

  var b = document.getElementById('modern-ui-body');

  if (!container.is(e.target) // if the target of the click isn't the container...
  && container.has(e.target).length === 0 
  && x.className === "infoArea-container infoArea__active" 
  && !container2.is(e.target) 
  &&  container2.has(e.target).length === 0) // ... nor a descendant of the container
  {
    x.className = "infoArea-container";
    b.style.overflow = 'auto';
  }
  else if (!container3.is(e.target) // if the target of the click isn't the container...
  && container3.has(e.target).length === 0 
  && y.className === "infoArea-container infoArea__active" 
  && !container4.is(e.target) 
  &&  container4.has(e.target).length === 0) // ... nor a descendant of the container
  {
    y.className = "infoArea-container";
    b.style.overflow = 'auto';
  }
}
);

$(document).on('touchstart', function (e)
{
  var container = $("#supportInfo"); // YOUR CONTAINER SELECTOR
  var container2 = $("#supportInfoButton");
  var x = document.getElementById("supportInfo");

  var container3 = $("#aboutInfo"); // YOUR CONTAINER SELECTOR
  var container4 = $("#aboutInfoButton");
  var y = document.getElementById("aboutInfo");

  var b = document.getElementById('modern-ui-body');

  if (!container.is(e.target) // if the target of the click isn't the container...
  && container.has(e.target).length === 0 
  && x.className === "infoArea-container infoArea__active" 
  && !container2.is(e.target) 
  &&  container2.has(e.target).length === 0) // ... nor a descendant of the container
  {
    x.className = "infoArea-container";
    b.style.overflow = 'auto';
  }
  else if (!container3.is(e.target) // if the target of the click isn't the container...
  && container3.has(e.target).length === 0 
  && y.className === "infoArea-container infoArea__active" 
  && !container4.is(e.target) 
  &&  container4.has(e.target).length === 0) // ... nor a descendant of the container
  {
    y.className = "infoArea-container";
    b.style.overflow = 'auto';
  }
}
);


function readMoreFunc() {
  var dots = document.getElementById("dots");
  var moreText = document.getElementById("more");
  var btnText = document.getElementById("myBtn");

  if (dots.style.display === "none") {
    dots.style.display = "inline";
    btnText.innerHTML = "Read more"; 
    moreText.style.display = "none";
  } else {
    dots.style.display = "none";
    btnText.innerHTML = "Read less"; 
    moreText.style.display = "inline";
  }
}

//var element = document.getElementsByClassName("ui-dialog-titlebar-close");
//var textnode = "<span aria-hidden='true'>&times;</span>";
//element.innerHTML = "<span aria-hidden='true'>&times;</span>";

/* var node = document.createElement("SPAN");
var textnode = document.createTextNode("Test");
node.appendChild(textnode);
document.getElementsByClassName("ui-dialog-titlebar-close").appendChild(node); */

function show_message(target) {
  $(document).ready(function(){
    if (!target) {
        target='toast';
    }
    var t = document.getElementsByClassName(target);
      $('.'+target).toast('show');
      if(t.className == target+' show'){
          $('.'+target).fadeOut(2000);
    }
  });
}


