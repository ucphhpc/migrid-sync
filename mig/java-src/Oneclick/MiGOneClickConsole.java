/*
# MiGOneClickConsole - OneClick resource app
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

import java.lang.Thread;
import java.lang.reflect.Method;

import java.net.URL;
import java.net.URLClassLoader;

import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.BufferedReader;
import java.io.BufferedWriter;

import MiG.oneclick.HttpsConnection;

public class MiGOneClickConsole
{
   private boolean oneshot;
   private String MiG_server;
   private String sandboxkey_filename;
   private String resource_request_url_str;
   private String codebase;
   private String code;
   private String archive;
   private String server;
   private String sandboxkey;
   private String resource_name;
   private String cputime;
   private Thread resource_thread;

   
   private MiGOneClickConsole(String MiG_server, String sandboxkey_filename, boolean oneshot)
     {
	this.MiG_server = MiG_server;
	this.sandboxkey_filename = sandboxkey_filename;
	this.oneshot = oneshot;
	this.resource_request_url_str = "https://" + this.MiG_server + "/cgi-sid/oneclick.py?console=true";
	
	this.codebase = null;
	this.code = null;
	this.archive = null;
	this.server = null;
	this.sandboxkey = null;
	this.resource_name = null;
	this.cputime = null;
     }
   
   private int init() throws Exception
     {
	int resource_request_rc;
	
	String readline;
		
	BufferedReader BR;
	BufferedWriter BW;
	
	File sandboxkey_file;
	HttpsConnection resource_request_conn;
		
	// If sandboxkey exists, send it with the request.
	sandboxkey_file = new File(sandboxkey_filename);
	if (sandboxkey_file.exists())
	  {
	     BR = new BufferedReader( new FileReader( sandboxkey_file ));
	     this.sandboxkey = BR.readLine();
	     BR.close();
	  }
		
	// Make resource request to MiG server
	resource_request_conn = new HttpsConnection(this.resource_request_url_str, true);
	
	// Send sandboxkey as cookie
	if ( this.sandboxkey != null )
	  {
	     resource_request_conn.setRequestProperty("Cookie", this.sandboxkey.substring(0, this.sandboxkey.indexOf(";")));
	  }
		
	// Connect to MiG server
	resource_request_conn.open();
	resource_request_rc = resource_request_conn.getResponseCode();
	if ( resource_request_rc == HttpsConnection.HTTP_OK )
	  {
	     // If new resource created store sandboxkey
	     this.sandboxkey = resource_request_conn.getHeaderField("Set-Cookie");
	     if (this.sandboxkey != null)
	       {
		  BW = new BufferedWriter( new FileWriter( sandboxkey_file ));
		  BW.write(this.sandboxkey);
		  BW.newLine();
		  BW.close();
	       }
	     
	     // Read the responce from the server
	     readline = resource_request_conn.readLine();
	     while( readline != null )
	       {
		  //System.out.println("readline: " + readline);
		  if ( readline.indexOf("codebase: ") == 0 )
		    {
		       this.codebase = readline.substring(readline.indexOf(": ")+2, readline.length());
		    }
		  else if ( readline.indexOf("code: ") == 0 )
		    {
		       this.code = readline.substring(readline.indexOf(": ")+2, readline.length());
		    }
		  else if ( readline.indexOf("archive: ") == 0 )
		    {
		       this.archive = readline.substring(readline.indexOf(": ")+2, readline.length());
		    }
		  else if ( readline.indexOf("server: ") == 0 )
		    {
		       this.server = readline.substring(readline.indexOf(": ")+2, readline.length());
		    }
		  else if ( readline.indexOf("sandboxkey: ") == 0 )
		    {
		       this.sandboxkey = readline.substring(readline.indexOf(": ")+2, readline.length());
		    }
		  else if ( readline.indexOf("resource_name: ") == 0 )
		    {
		       this.resource_name = readline.substring(readline.indexOf(": ")+2, readline.length());
		    }
		  else if ( readline.indexOf("cputime: ") == 0 )
		    {
		       this.cputime = readline.substring(readline.indexOf(": ")+2, readline.length());
		    }
		  readline = resource_request_conn.readLine();
	       }
	  }
	resource_request_conn.close();
	
	System.out.println("Codebase: '" + this.codebase + "'");
	System.out.println("Code: '" + this.code + "'");
	System.out.println("archive: '" + this.archive + "'");
	System.out.println("server: '" + this.server + "'");
	System.out.println("sandboxkey: '" + this.sandboxkey + "'");
	System.out.println("resource_name: '" + this.resource_name + "'");
	System.out.println("cputime: '" + this.cputime + "'");
	
	return resource_request_rc;
     }
   
   
   
   private void start()
     {
	URLClassLoader urlClassLoader;
	Method init_method;
	Class resource_cl;
	Object resource_ob;
	
	do 
	  {
	     try
	       {
		  // Initiate URLClassloade
		  urlClassLoader = new URLClassLoader(
						      new URL[]
						      {
							 new URL(this.codebase + "/"),
							 new URL(this.codebase + "/" + this.archive)
						      }, 
						      null);
		  
		  // Load resource class from URLClassLoader
		  resource_cl = urlClassLoader.loadClass(this.code.substring(0,this.code.indexOf(".class")));
		  
		  // Create new instance of the resource class
		  resource_ob = resource_cl.newInstance();
		
		  // Get init method.
		  init_method = resource_cl.getMethod( "init", 
						  new Class[] 
						  { 
						     this.server.getClass(), 
						     this.sandboxkey.getClass(),
						     this.resource_name.getClass(),
						     this.cputime.getClass(),
						     Boolean.valueOf(this.oneshot).getClass(),
						     urlClassLoader.getClass()
						  });
		  
		  // Invoke init method
		  init_method.invoke( resource_ob, 
				      new Object[] 
				      {
					this.server, 
					this.sandboxkey, 
					this.resource_name,
					this.cputime,
					Boolean.valueOf(this.oneshot),
					urlClassLoader
				      });
		  
		  // Create new resource thread
		  this.resource_thread = new Thread((Runnable) resource_ob);
		  
		  // Start new thread
		  this.resource_thread.start();
		  
		  // Wait new thread to end (hopefully this never happens,
		  // because the the thread died.
		  this.resource_thread.join();
	       }
	     catch ( Exception e )
	       {
		  System.out.println("Resource Thread DIED:");
		  e.printStackTrace();
		  System.out.println("Sleeping 60 secs, then starting a new one.");
		  try
		    {
		       Thread.sleep(60000);
		    }
		  catch ( Exception e2 ) {e2.printStackTrace();}
	       }
	  } while(!this.oneshot);
     } 
   
   public static void main(String[] argv)
     {
	boolean oneshot;
	int init_rc;
	
	MiGOneClickConsole mocc;
	  
	if (argv.length < 2 || argv.length > 3)
	  {
	     System.out.println("USAGE: MiGResourceApp MiGServer sandboxkey_file [oneshot=0|1]");
	  }
	else
	  {
	     try
	       {
		  oneshot = false;
		  if (argv.length == 3 && Integer.parseInt(argv[2]) == 1)
		    {
		       oneshot = true;
		    }
		  
		  mocc = new MiGOneClickConsole(argv[0], argv[1], oneshot);
		  init_rc = mocc.init();
		  if ( init_rc == HttpsConnection.HTTP_OK )
		    {
		       mocc.start();
		    }
		  else
		    {
		       System.out.println("Could'nt connect to MiG server: " + argv[0] + " RC: " + init_rc);
		    }
	       }
	     catch( Exception e )
	       {
		  e.printStackTrace();
	       }
	  }
     }
} 
