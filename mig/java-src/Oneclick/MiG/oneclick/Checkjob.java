/*
# Checkjob - OneClick check job liveness
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

import java.lang.reflect.Method;
import java.lang.reflect.Modifier;

import java.io.ObjectInputStream;
import java.net.URL;
import java.net.URLClassLoader;
import javax.net.ssl.HttpsURLConnection;

public class Checkjob implements Runnable
{
   private final int SLEEPTIME_FACTOR = 1000;
   
   private boolean alive;
   private boolean job_active;
   private String server;
   private String iosessionid;
   private long sleep_period;
   
   public Checkjob(String server, String iosessionid)
     {
	this.alive = true;
	this.job_active = true;
	this.server = server;
	this.iosessionid = iosessionid;
	this.sleep_period = 60;
     }
   
   public boolean jobActive()
     {
	return this.job_active;
     }
   
      
   // We have been stopped
   public void stop()
     {
	this.alive = false;
     }
   
   // We have been destroyed
   public void destroy()
     {
	this.alive = false;
     }
   
   // Retrieves the files needed and executes the vmplayer 
   public void run()
     {
	int checkjob_rc;
	String checkjob_url;
	String value;
	HttpsConnection checkjob_conn;
	String readline;
	
	try
	  {
	     checkjob_url = this.server + "/cgi-sid/isjobactive.py?iosessionid=" + this.iosessionid;
	     System.out.println("Job check URL:" + checkjob_url);
	     
	     while (this.alive && this.job_active)
	       {
		  // Request jobstatus
		  checkjob_conn = new HttpsConnection(checkjob_url);
		  checkjob_conn.open();
	     
		  // Check if request went ok
		  if (checkjob_conn.getResponseCode() == HttpsConnection.HTTP_OK )
		    {
		       readline = checkjob_conn.readLine();
		       //System.out.println("readline: " + readline);
		       if (Integer.parseInt(readline) == HttpsConnection.MIG_CGI_ERROR)
			 {
			    this.job_active = false;
			 }
		    }
		  checkjob_conn.close();
		  Thread.sleep(this.sleep_period * this.SLEEPTIME_FACTOR);
	       }
	  }
	
	catch (java.lang.Exception e)
	  {
	     e.printStackTrace();
	  }
     }
}


   
   
