/*
# HelloMiGOneClickWorld - Simple OneClick hello world app
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

import MiG.oneclick.File;
import MiG.oneclick.FileException;

public class HelloMiGOneClickWorld extends MiG.oneclick.Job
{
    public void MiG_main(String[] argv)
    {
	int i;
	int byte_counter;
	long starttime;
	long endtime;
	
	File in_file = null;
	File out_file = null;

	out("\n\nArgs:\n");
	for (i=0; i<argv.length; i++ )
	    out(argv[i] + "\n");

	byte_counter = 0;
	try {
	    starttime = System.currentTimeMillis();
	    in_file = this.open_file(argv[0], File.R);
	    if (in_file.getMode() != File.R)
		{
		    throw new FileException("Could'nt open file for read: " + argv[0]);
		}
	       
	    out_file = this.open_file(argv[1], File.W);
	    if (out_file.getMode() != File.W)
		throw new FileException("Could'nt open file for write: " + argv[1]);
	         
	    i=in_file.read();
	    while( i!= -1 ) {
		out_file.write(i);
		byte_counter = byte_counter + 1;
		i=in_file.read();
	    }
	       
	    out_file.close();
	    in_file.close();
	    endtime = System.currentTimeMillis();
	       
	    out("\nCopyed " + byte_counter + " bytes.");
	    out("\nCopy time: " + (endtime-starttime)/1000 + " seconds.");
	}
	catch (Exception e) {
	    err("\nHelloMiGOneClickWorld CAUGHT:\n" + e.getMessage());
	    err(MiG.oneclick.Exception.dumpStackTrace(e));
	    if (in_file != null)
		err("\n\nin_file errors:" + in_file.getErrorMessages());
	    if (out_file != null)
		err("\n\nout_file errors:" + out_file.getErrorMessages());
	}
    }
}
