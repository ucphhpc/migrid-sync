/*

#
# --- BEGIN_HEADER ---
#
# jquery.prettyprint - jquery based human readable units
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

*/

/* Enable strict mode to help catch tricky errors early */
"use strict";

/**
 * Returns on the form:
 * 800 -> 800 B
 * 1024 -> 1 KB
 * 1024*1024 -> MB
 * 1024*1024*1024 -> GB
 */
function pp_bytes(bytes) {
  
    var temp = '';
    if (bytes < 1024) {
	temp ='B';
    } else if (bytes < 1048576) {
	bytes = bytes/1024;
	temp = 'KB';
    } else if (bytes < 1073741824) {
	bytes = bytes/1048576;
	temp = 'MB';
    } else if (bytes < 1099511627776) {
	bytes = bytes/1073741824;
	temp = 'GB';
    }
  
    return bytes.toFixed(2)+' '+temp;
  
}

function pp_prefix(test) {
    if (test < 10) {
	test = "0"+test;
    }
    return test;
}

function pp_date(time) {
  
    var aDate = new Date(time*1000);
    // getMonth returns zero indexed number
    return aDate.getFullYear() + '-'+
        pp_prefix(aDate.getDate()) + '-'+
        pp_prefix(aDate.getMonth()+1) + ' '+
        pp_prefix(aDate.getHours()) + ':'+
        pp_prefix(aDate.getMinutes());
  
}
