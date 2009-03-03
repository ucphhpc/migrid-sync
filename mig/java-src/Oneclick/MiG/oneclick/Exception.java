/*
# Exception - Exception wrapper
# Copyright (C) 2007  Martin Rehr
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
*/

package MiG.oneclick;

public class Exception extends java.lang.Exception
{
   // Constructor
   public Exception(String message)
     {
	super(message);
     }
   
   
    // Return the stacktrace as a string
   public static String dumpStackTrace( java.lang.Exception e )
     {
	int i;
	String result;
	
	result = "\n--------------- Begin stacktrace ----------------\n" + e + "\n";
	for( i=0; i<e.getStackTrace().length; i++ )
	  {
	     result = result + e.getStackTrace()[i].toString() + "\n";
	  }
	result = result + "\nCaused by:\n";
	
	if (e.getCause() != null )
	  {
	     for( i=0; i<e.getCause().getStackTrace().length; i++ )
	       {
		  result = result + e.getCause().getStackTrace()[i].toString() + "\n";
	       }  
	  }
	result = result + "\n---------------- End stacktrace -----------------\n";
	return result;
     }

}
