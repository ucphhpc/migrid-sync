/*

#
# --- BEGIN_HEADER ---
#
# ui-extra - UI V3 specific but skin-independent helper functions
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

// MAIN MENU FUNCTION
function hamburgerMenuToggle() {
  var x = document.getElementById("hamMenu");
  var y = document.getElementById("hamBtn");
  var z = document.getElementById("menuTxt");
  var v = document.getElementsByClassName("is-active");
    console.log("ham toggle start");
  if (x.className === "slidernav-container") {
    x.className = "slidernav-container slidernav-active";
    y.className = "hamburger hamburger--vortex is-active";
    if (z !== null) {
      z.innerHTML = "Close"
    }
    v.className = "infoArea-container";
  } else {
    x.className = "slidernav-container";
    y.className = "hamburger hamburger--vortex";
    if (z !== null) {
      z.innerHTML = "Menu"
    }
  }
    console.log("ham toggle done");
}

$(document).mouseup(function (e)
{
    console.log("mouse up start");
  var container = $("#hamMenu"); // YOUR CONTAINER SELECTOR
  var container2 = $("#sideBar");
  var x = document.getElementById("hamMenu");
  var y = document.getElementById("hamBtn");
  var z = document.getElementById("menuTxt");

  if (!container.is(e.target) // if the target of the click isn't the container...
  && container.has(e.target).length === 0 
  && x !== null
  && x.className === "slidernav-container slidernav-active" 
  && !container2.is(e.target) 
  &&  container2.has(e.target).length === 0) // ... nor a descendant of the container
  {
    x.className = "slidernav-container";
    y.className = "hamburger hamburger--vortex";
    if (z !== null) {
      z.innerHTML = "Menu"
    }
  }
    console.log("mouse up done");
}
);

$(document).on('touchstart', function (e)
{
  var container = $("#hamMenu"); // YOUR CONTAINER SELECTOR
  var container2 = $("#sideBar");
  var x = document.getElementById("hamMenu");
  var y = document.getElementById("hamBtn");
  var z = document.getElementById("menuTxt");

  if (!container.is(e.target) // if the target of the click isn't the container...
  && container.has(e.target).length === 0 
  && x !== null
  && x.className === "slidernav-container slidernav-active" 
  && !container2.is(e.target) 
  &&  container2.has(e.target).length === 0) // ... nor a descendant of the container
  {
    x.className = "slidernav-container";
    y.className = "hamburger hamburger--vortex";
    if (z !== null) {
      z.innerHTML = "Menu"
    }
  }
}
);


// USERMENU FUNCTIONS
function userMenuToggle() {
  var x = document.getElementById("userMenu");
  var y = document.getElementById("hamMenu");
  var z = document.getElementById("hamBtn");
  var v = document.getElementById("menuTxt");
  if (x.className === "popup-container popup-active") {
    x.className = "popup-container";
  } else {
    x.className = "popup-container popup-active";
    y.className = "slidernav-container";
      z.className = "hamburger hamburger--vortex";
    if (v !== null) {
      v.innerHTML = "Menu"
    }
  }
}

$(document).mouseup(function (e)
{
  var container = $("#userMenu"); // YOUR CONTAINER SELECTOR
  var container2 = $("#userMenuButton");
  var x = document.getElementById("userMenu");

  if (!container.is(e.target) // if the target of the click isn't the container...
  && container.has(e.target).length === 0 
  && x !== null
  && x.className === "popup-container popup-active" 
  && !container2.is(e.target) 
  &&  container2.has(e.target).length === 0) // ... nor a descendant of the container
  {
    x.className = "popup-container";
  }
}
);

$(document).on('touchstart', function (e)
{
  var container = $("#userMenu"); // YOUR CONTAINER SELECTOR
  var container2 = $("#userMenuButton");
  var x = document.getElementById("userMenu");

  if (!container.is(e.target) // if the target of the click isn't the container...
  && container.has(e.target).length === 0 
  && x !== null
  && x.className === "popup-container popup-active" 
  && !container2.is(e.target) 
  &&  container2.has(e.target).length === 0) // ... nor a descendant of the container
  {
    x.className = "popup-container";
  }
}
);

// ONLY ON HOME.PY - ADD APPLICATIONS
function addApp() {
  var x = document.getElementById("add-app__window");
  var b = document.getElementById('modern-ui-body');
  console.log(b);
  if (x.className === "app-container") {
    x.className = "app-container is-active";
    b.style.overflow = 'hidden';
  } else {
    x.className = "app-container";
    b.style.overflow = 'auto';
  }
}



