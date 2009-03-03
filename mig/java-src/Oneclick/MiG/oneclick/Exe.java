/*
# Exe - OneClick resource exe
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

public class Exe implements Runnable
{
   private final int SLEEPTIME_FACTOR = 1000;
   
   private String server;
   private String iosessionid;
   private String jobid;
   private String execute_cmd;
   private String[] execute_args;
   private StringBuffer stderr;
   private StringBuffer stdout;

   private Method MiG_main_method;
   private Method getStdout_method;
   private Method getStderr_method;
   private Method setInfo_method;
   private Method restoreCheckpointedFiles_method;
   private URLClassLoader urlClassLoader;

   
   public Exe(URLClassLoader urlClassLoader, 
		     String server, 
		     String iosessionid, 
		     String jobid, 
		     String execute_cmd, 
		     String[] execute_args)
     {
	this.urlClassLoader = urlClassLoader;
	this.server = server;
	this.iosessionid = iosessionid;
	this.jobid = jobid;
	this.execute_cmd = execute_cmd;
	this.execute_args = execute_args;
	this.stderr = new StringBuffer();
	this.stdout = new StringBuffer();
	this.MiG_main_method = null;
	this.getStdout_method = null;
	this.getStderr_method = null;
	this.setInfo_method = null;
     }

   
   // Check if the execute_str conntains a sleep job.
   // if this is the case return the millis to sleep.
   // otherwise -1 is returned.
   private long checkForSleepJob(String execute_str, String[] execute_args) throws java.lang.Exception
     {
	long sleeptime = -1;
	if (execute_str.indexOf("sleep " ) == 0 )
	  {
	     // We found sleep command, try to extract how long to sleep

	  }
	return sleeptime;
     }


   private void getJobMethods(Class job_class) throws NoSuchMethodException
     {
	int mods;

	// Get 'boolean restoreCheckpointedFiles()' method, and check if is has the right modifiers
	this.restoreCheckpointedFiles_method = job_class.getMethod("restoreCheckpointedFiles", new Class[] {});
	mods = restoreCheckpointedFiles_method.getModifiers();
	if ( this.restoreCheckpointedFiles_method.getReturnType() != boolean.class || Modifier.isStatic(mods) || !Modifier.isPublic(mods))
	  {
	     throw new NoSuchMethodException("StringBuffer boolean restoreCheckpointedFiles()");
	  }
	
	// Get 'void MiG_main(String[] argv)' method, and check if is has the right modifiers
	this.MiG_main_method = job_class.getMethod("MiG_main", new Class[] {this.execute_args.getClass()});
	mods = this.MiG_main_method.getModifiers();
	if ( this.MiG_main_method.getReturnType() != void.class || Modifier.isStatic(mods) || !Modifier.isPublic(mods))
	  {
	     throw new NoSuchMethodException("MiG_main(String[] argv)");
	  }
	
	// Get the 'StringBuffer getStdout()' method, and check if is has the right modifiers.
	this.getStdout_method = job_class.getMethod("getStdout", null );
	mods = this.getStdout_method.getModifiers();
	if ( this.getStdout_method.getReturnType() != StringBuffer.class || Modifier.isStatic(mods) || !Modifier.isPublic(mods))
	  {
	     throw new NoSuchMethodException("StringBuffer getStdout()");
	  }
	
	// Get the 'StringBuffer getStderr()' method, and check if is has the right modifiers.
	this.getStderr_method = job_class.getMethod("getStderr", null );
	mods = this.getStderr_method.getModifiers();
	if ( this.getStderr_method.getReturnType() != StringBuffer.class || Modifier.isStatic(mods) || !Modifier.isPublic(mods))
	  {
	     throw new NoSuchMethodException("StringBuffer getStderr()");
	  }
	
	// Get the 'void setInfo(String server, String session_id)' method, and check if is has the right modifiers.
	this.setInfo_method = job_class.getMethod("setInfo", new Class[]{this.server.getClass(), this.iosessionid.getClass(), this.jobid.getClass()});
	mods = this.setInfo_method.getModifiers();
	
	if ( this.setInfo_method.getReturnType() != void.class || Modifier.isStatic(mods) || !Modifier.isPublic(mods))
	  {
	     throw new NoSuchMethodException("void setInfo(String server, String session_id )");
	  }
     }
   
   // Retrieves object to execute
   private Object getCheckpointObject()
     {
	int checkpoint_nr;
	int mods;

	Boolean filerestore_result;
	String checkpoint_url_str;
	String checkpoint_request_url_str;
	URL checkpoint_obj_url;
	
	HttpsConnection checkpoint_request_conn;
	HttpsURLConnection httpsUrlConn;
	
	Class job_class;
	Object job_object;
	Object result;
	ObjectInputStream ois;

	Method restoreCheckpointedFiles_method;
	
	result = null;	
	try 
	  {
	     // Generate checkpoint status url
	     checkpoint_url_str = this.server + "/sid_redirect/" + this.iosessionid + "/" + this.jobid + "." + this.execute_cmd + ".checkpoint";
	     checkpoint_request_url_str = checkpoint_url_str + ".latest";
	     
	     System.out.println("checkpoint_request_url_str: " + checkpoint_request_url_str);
	     
	     checkpoint_request_conn = new HttpsConnection(checkpoint_request_url_str);
	     checkpoint_request_conn.open();
	     
	     checkpoint_nr = -1;
	     // Check if request went ok
	     if (checkpoint_request_conn.getResponseCode() == HttpsConnection.HTTP_OK )
	       {
		  checkpoint_nr = Integer.parseInt(checkpoint_request_conn.readLine());
	       }
	     checkpoint_request_conn.close();
	     
	     if (checkpoint_nr != -1)
	       {
		  // Generate checkpoint url
		  checkpoint_obj_url = new URL(checkpoint_url_str + "." + checkpoint_nr);
		  System.out.println("checkpoint obj url: " + checkpoint_obj_url);
		  
		  // Retrieve object
		  httpsUrlConn = (HttpsURLConnection) checkpoint_obj_url.openConnection();
		  httpsUrlConn.connect();
		  job_object = (Object) (new ObjectInputStream(httpsUrlConn.getInputStream())).readObject();
		  httpsUrlConn.getResponseCode();
		  httpsUrlConn.disconnect();
		 
		  job_class = job_object.getClass();
		  
		  // Check if object is a oneclick job
		  this.getJobMethods(job_class);
		  
		  // Setting the executing information of this session to checkpointed job
		  this.setInfo_method.invoke(job_object, new Object[]{this.server, this.iosessionid, this.jobid});
		  
		  result = job_object;
		  	
		  // Try to restore checkpointed files assosiated with this job
		  filerestore_result = (Boolean) this.restoreCheckpointedFiles_method.invoke(job_object, new Object[]{});
		  if (!filerestore_result.booleanValue())
		    {
		       // Failed to restore checkpointed files, discarding checkpoint
		       result = null;
		    }
	       }
	  }
	catch (java.lang.Exception e)
	  {
	     result = null;
	     // Retrieving of checkpoint failed.
	     e.printStackTrace();
	  }
	return result;
     }

   public StringBuffer getStdout()
     {
	return this.stdout;
     }
   
   public StringBuffer getStderr()
     {
	return this.stderr;
     }
   
   
   // Retrieves the files needed and executes the vmplayer 
   public void run()
     {
	int mods;
	long sleeptime; 
	
	StringBuffer job_stderr;
	StringBuffer job_stdout;
	
	Class job_class;
	Object job_object;
		
	try
	  {
	     // If sleep job, sleep
	     if ( this.execute_cmd.compareTo("sleep") == 0 )
	       {
		  sleeptime = Long.parseLong(execute_args[0]) * SLEEPTIME_FACTOR;
		  Thread.sleep(sleeptime);
	       }
	     else
	       {
		  // // Load execute job class
		  job_object = this.getCheckpointObject();
		  
		  if (job_object == null)
		    {
		       // No checkpoint available
		       job_class = this.urlClassLoader.loadClass(this.execute_cmd);
		       this.getJobMethods(job_class);
		    }
		  else
		    {
		       // Found checkpoint
		       job_class = job_object.getClass();
		    }
		  		  
		  // All Needed methods exists, if not checkpointed object, create new instance of the execute_class	    
		  if (job_object == null)
		    {
		       job_object = job_class.newInstance();
		    
		       // Setting the executing information of this job
		       this.setInfo_method.invoke(job_object, new Object[]{this.server, this.iosessionid, this.jobid});
		    }
		  
		  // invoke the 'MiG_main' method of the job with the give arguments.
		  this.MiG_main_method.invoke(job_object, new Object[] {execute_args});
		  
		  job_stderr = (StringBuffer) this.getStderr_method.invoke(job_object, null );
		  this.stderr.append(job_stderr);
		  
		  job_stdout = (StringBuffer) this.getStdout_method.invoke(job_object, null );
		  this.stdout.append(job_stdout);
	       }
	  }
	catch (java.lang.Exception e)
	  {
	     e.printStackTrace();
	     this.stderr.append( MiG.oneclick.Exception.dumpStackTrace(e) );
	  }
     }
}

   
   
