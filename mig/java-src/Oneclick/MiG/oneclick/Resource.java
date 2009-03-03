/*
# Resource - OneClick resource
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

import java.lang.Thread;
import java.lang.reflect.Array;

import java.util.Vector;

import java.net.URL;
import java.net.URLClassLoader;

import java.awt.Image;

public class Resource implements Runnable
{
   //public final static int APPLET = 1;
   //public final static int CONSOLE = 2;
   
   private final int HTTP_OK = 200;
   private final int HTTP_NOT_FOUND = 404;
   
   private final int MIG_JOB_EXIT_OK = 0;
   private final int MIG_JOB_EXIT_ERROR = 1;
   private final int MIG_JOB_EXIT_SERVERINTERUPT = 2;
   
   private final int JOB_GENERATE_WAIT_TIME = 1000;
   private final int SEND_JOB_RETRY_TIME = 1000;

   // java uses milis sleep, MiG uses secs
   private final int SLEEPTIME_FACTOR = 1000;
   private final int JOB_FINISH_CHECK_SLEEPTIME = 15;
     
   public final int INITIALIZING = 0;
   public final int RETRIEVING_JOB = 1;
   public final int EXECUTING_JOB = 2;
   public final int SENDING_RESULT = 3;
   public final int JOB_FINISHED = 4;
   public final int FAILED = 5;

   private boolean alive;
   private boolean oneshot;
   private int status;
   private int exit_value;
   private int jobs_done;
   private int jobs_failed;
   private int execute_image_counter;
   private String status_msg;
   private String server;
   private String sandboxkey;
   private String resource_name;
   private String cputime;
   private String request_joburl;
   private String mig_sessionid;
   private String mig_iosessionid;
   private String mig_jobid;
   private String current_jobname;
   private StringBuffer stderr;
   private StringBuffer stdout;
   private Vector executables;
   private MiG.oneclick.Applet applet;
   private Image execute_image;
   private URLClassLoader urlClassLoader;

   private Checkjob checkjob;
   private Thread checkjob_thread;
   
   // Constructors
   public Resource()
     {
	this.applet = null;
     }
   
   public Resource(MiG.oneclick.Applet applet) throws java.lang.Exception
     {
	this.applet = applet;
	this.init( this.applet.getParameter("server"), 
		   this.applet.getParameter("sandboxkey"), 
		   this.applet.getParameter("resource_name"),
		   this.applet.getParameter("cputime"),
		   Boolean.valueOf(false),
		   URLClassLoader.newInstance(new URL[]{}, this.applet.getClass().getClassLoader())
		 );
	
     }
      
   public void init( String server, 
		     String sandboxkey, 
		     String resource_name,
		     String cputime,
		     Boolean oneshot,
		     URLClassLoader urlClassLoader
		   ) throws java.lang.Exception
     {
	this.alive = true;
	this.status = -1;
	this.status_msg = "";
	this.jobs_done = 0;
	this.jobs_failed = 0;
	this.server = server;
	this.sandboxkey = sandboxkey;
	this.resource_name = resource_name;
	this.cputime = cputime;
	this.oneshot = oneshot.booleanValue();
	this.urlClassLoader = urlClassLoader;
	this.mig_sessionid = null;
	this.mig_iosessionid = null;
	this.mig_jobid = null;
	this.exit_value = -1;
	this.execute_image_counter = 0;
	this.stderr = new StringBuffer();
	this.stdout = new StringBuffer();
	this.executables = new Vector();
	this.request_joburl = this.server + "/cgi-sid/requestnewjob?unique_resource_name=" + this.resource_name + "&cputime=" + this.cputime + "&sandboxkey=" + this.sandboxkey + "&exe=jvm";
	this.execute_image = null;
	this.checkjob = null;
	this.checkjob_thread = null;
     }
      
   // We have been stopped
   public void stop()
     {
	System.out.println("Resource STOP");
	this.alive = false;
     }
   
   // We have been destroyed
   public void destroy()
     {
	this.alive = false;
	System.out.println("Resource DESTROY");
     }
   
   public int getStatus()
     {
	return this.status;
     }
   
   public String getStatusMsg()
     {
	return this.status_msg;
     }

   public String getServer()
     {
	return this.server;
     }

   public String getResourceName()
     {
	return this.resource_name;
     }

   public int getJobsDone()
     {
	return this.jobs_done;
     }
      
   public int getJobsFailed()
     {
	return this.jobs_failed;
     }
   
   public Image getExecuteImage()
     {
	return this.execute_image;
     }
        
   private void setStatus(int status, String status_msg)
     {
	this.status = status;
	this.status_msg = status_msg;
	if (this.applet != null)
	  {
	     this.applet.repaint();
	  }
     }
   			   
   // Retrieve new job
   private boolean retrieveJob()
     {
	boolean result;
	
	int getinputfiles_rc;
	String request_joburl;
	String getinputfiles_url;
	String readline;
	HttpsConnection job_request_conn;
	HttpsConnection getinputfiles_conn;
	
	result = false;
	try
	  {
	     this.setStatus(this.RETRIEVING_JOB, "Retrieving new job.");
	     
	     // Generate job name
	     this.current_jobname = String.valueOf(System.currentTimeMillis());
	     
	     // Request job
	     request_joburl = this.request_joburl + "&localjobname=" + this.current_jobname;
	     job_request_conn = new HttpsConnection(request_joburl);
	     job_request_conn.open();
	     
	     // Check if request went ok
	     if (job_request_conn.getResponseCode() == HttpsConnection.HTTP_OK )
	       {
		  readline = job_request_conn.readLine();
		  if (Integer.parseInt(readline) == HttpsConnection.MIG_CGI_OK)
		    {
		       // Job requestet ok, retrive jobdescription file.
		       // Loop until it's available, the scheduler has to create the job.
		       getinputfiles_rc = HttpsConnection.HTTP_NOT_FOUND;
		       while( getinputfiles_rc != HttpsConnection.HTTP_OK )
			 {
			    // Give the MiG server time to generate job
			    Thread.sleep(JOB_GENERATE_WAIT_TIME);
			    
			    getinputfiles_url = this.server + "/sid_redirect/" + this.current_jobname + ".getinputfiles";
			    System.out.println("getinputfiles_url: " + getinputfiles_url);
			    
			    getinputfiles_conn = new HttpsConnection(getinputfiles_url);
			    getinputfiles_conn.open();
			    getinputfiles_rc = getinputfiles_conn.getResponseCode();
			    
			    // If jobdescription file exists read mig_iosession_id and job_id from it.
			    if ( getinputfiles_rc == HttpsConnection.HTTP_OK )
			      {
				 readline = getinputfiles_conn.readLine();
				 while( readline != null )
				   {
				      //System.out.println("readline: " + readline);
				      if ( readline.indexOf("mig_session_id: ") == 0 )
					{
					   this.mig_sessionid = readline.substring(readline.indexOf(": ")+2, readline.length());
					}
				      else if ( readline.indexOf("mig_iosession_id: ") == 0 )
					{
					   this.mig_iosessionid = readline.substring(readline.indexOf(": ")+2, readline.length());
					}
				      else if ( readline.indexOf("job_id: ") == 0 )
					{
					   this.mig_jobid = readline.substring(readline.indexOf(": ")+2, readline.length());
					}
				      else if ( readline.indexOf("executables: ") == 0 )
					{
					   this.executables.add( readline.substring(readline.indexOf(": ")+2, readline.length()) );
					}
				      readline = getinputfiles_conn.readLine();
				   }
				 if (this.mig_sessionid != null && this.mig_iosessionid != null && this.mig_jobid != null )
				   result = true;
			      }
			    getinputfiles_conn.close();
			 }
		    }
	       }
	     job_request_conn.close();
	  }
	catch (java.lang.Exception e)
	  {
	     result = false;
	     e.printStackTrace();
	  }
	return result;
     }
   
   // Build a vector containing execute lines
   private Vector getExecuteVector() throws java.lang.Exception 
     {
	int job_rc;
	String joburl;
	String readline;
	Vector execute_vector;
	
	HttpsConnection job_conn;

	execute_vector = new Vector();
	
	// Generate jobdescriptionfile url
	joburl = this.server + "/sid_redirect/" + this.mig_sessionid + ".job";
	job_conn = new HttpsConnection(joburl);
	job_conn.open();
	job_rc = job_conn.getResponseCode();
		
	// If connection to jobdecriptionfile went ok, retrieve information
	if ( job_rc == HttpsConnection.HTTP_OK )
	  {
	     readline = job_conn.readLine();
	     while( readline != null )
	       {
		  // If we found an exeute command, Add to execute vector
		  if ( readline.indexOf("execute: ") == 0 )
		    {
		       execute_vector.addElement( readline.substring(readline.indexOf(": ")+2, readline.length()) );
		    }
		  readline = job_conn.readLine();
	       }
	  }
	job_conn.close();
	
	return execute_vector;
     }
   
   /* NOT used at the moment, as we can't change codebase in the default applet security model 
    * The codebase is changed by symlink changing on the server
    
   // Return the url of the class to be executed
   private URL[] getExecutablesUrls() throws java.lang.Exception
     {
	for (i=0; i<this.executables.size(); i++)
	  {
	     executable_url_str = this.server + "/sid_redirect/" + this.mig_iosessionid + "/" + (String) this.executables.elementAt(i);
	     // Only class files is allowed as executables.
	     // Jar files is _NOT_ allowed as they can be signed and 
	     // trick the resource to allow nasty things to occur.
	     if (executable_url_str.indexOf(".class") == executable_url_str.length()-6)
	       {
		  System.out.println("Adding: " + executable_url_str);
		  url_vector.add(new URL(executable_url_str));
	       }
	  }
	// Add the MiG codebase url
	url_vector.add(oneclick_codebase_url);
	
	return (URL[]) url_vector.toArray(result);
     }
   */

   // Return the execute args from the execute_arr
   // The first elem in execute_arr is the execute_cmd 
   // which is not part of the args in java
   private String[] getExecuteArgs(String[] execute_arr) throws java.lang.Exception
     {
	int i;
	String[] execute_args = null;
	
	if (execute_arr.length > 0)
	  {
	     execute_args = (String[]) Array.newInstance(Class.forName("java.lang.String") ,execute_arr.length-1);
	     for (i=1; i<execute_arr.length; i++)
	       {
		  execute_args[i-1] = execute_arr[i];
	       }
	  }
	return execute_args;
     }

   
   private void printDebugInfo(String execute_cmd, String[] execute_args)
     {
	int i;
		
	//System.out.println("oneclick_codebase_url: " + this.apple.getCodeBase());
	System.out.println("Execute_cmd: " + execute_cmd);
	for (i=0; i<execute_args.length; i++)
	  {
	     System.out.println("Execute args[" + i + "]: " + execute_args[i]);
	  }
     }
   
   
   private void retrieveExecuteImage( String execute_cmd )
     {
	int rc;
	
	String image_url_str;
	HttpsConnection image_conn;
	  	
	if ( this.applet != null )
	  {
	     image_url_str = this.applet.getCodeBase() + execute_cmd + this.execute_image_counter + ".gif";
	
	     //System.out.println("image url: " + image_url_str);
	     try
	       {
		  image_conn = new HttpsConnection(image_url_str);
		  image_conn.open();
		  rc = image_conn.getResponseCode();
		  image_conn.close();
		  
		  if ( rc == HttpsConnection.HTTP_OK )
		    {
		       this.execute_image = this.applet.getImage(new URL(image_url_str));
		       this.execute_image_counter++;
		    }
		  else if (this.execute_image_counter > 0)
		    {
		       // Image does'nt exist, try resetting image counter
		       this.execute_image_counter = 0;
		       image_url_str = this.applet.getCodeBase() + execute_cmd + this.execute_image_counter + ".gif";
		       //System.out.println("image url2: " + image_url_str);
		       
		       image_conn = new HttpsConnection(image_url_str);
		       image_conn.open();
		       rc = image_conn.getResponseCode();
		       image_conn.close();
		       
		       if ( rc == HttpsConnection.HTTP_OK )
			 {
			    this.execute_image = this.applet.getImage(new URL(image_url_str));
			    this.execute_image_counter++;
			 }
		       else
			 {
			    this.execute_image = null;
			 }
		    }
	       }
	     catch (java.lang.Exception e)
	       {
		  System.out.println("CAUGHT: " + e);
		  this.execute_image = null;
	       }
	  }
     }
   
      
   // Execute the job
   private void execute()
     {
	int i;
	int mods;
	long sleeptime;

	String execute_msg;
	String execute_str;
	String execute_cmd;
	String[] execute_arr;
	String[] execute_args;

	StringBuffer job_stderr;
	StringBuffer job_stdout;
	Vector execute_vector;

	Exe exe;
		
	Thread exe_thread;
		
	try
	  {
	     this.exit_value = MIG_JOB_EXIT_OK;
	          
	     execute_vector = this.getExecuteVector();
	     System.out.println("execute_vector size: " + execute_vector.size());
	
	     //Iterate execute_vector and execute commands found in it.
	     i=0;
	     while( this.exit_value == MIG_JOB_EXIT_OK && i<execute_vector.size() )
	       {
		  execute_str = (String) execute_vector.elementAt(i);
		  System.out.println("execute_str: '" + execute_str + "'");
		  
		  // Determine execute command and args
		  //execute_arr = execute_arr[execute_arr.length-1].split(" ");
		  execute_arr = execute_str.split(" ");
		  
		  // The execute command is the first arg
		  execute_cmd = execute_arr[0];
		  
		  // Determine the args to the execute command
		  execute_args = this.getExecuteArgs(execute_arr);
		  
		  // Debug onfo
		  this.printDebugInfo(execute_cmd, execute_args);
		  
		  // Retrieve image to be shown at execution.
		  this.retrieveExecuteImage( execute_cmd );
		  
		  // Set status msg
		  execute_msg = "Executing: '" + execute_cmd;
		  for (int j=0; j<execute_args.length;j++)
		    {
		       execute_msg += " " + execute_args[j];
		    }
		  execute_msg += "'";
		  this.setStatus(this.EXECUTING_JOB, execute_msg); 
		  
		  
		  exe = new Exe(this.urlClassLoader,
				this.server,
				this.mig_iosessionid,
				this.mig_jobid,
				execute_cmd,
				execute_args);
		  
		  
		  
		  exe_thread = new Thread(exe);
		  exe_thread.start();
		  
		  while (exe_thread.isAlive())
		    {
		       //System.out.println("Waiting for exe_thread to finish.");
		       Thread.sleep(JOB_FINISH_CHECK_SLEEPTIME * SLEEPTIME_FACTOR);
		       
		       if (!this.checkjob.jobActive())
			 {
			    exe_thread.stop();
			    this.exit_value = MIG_JOB_EXIT_SERVERINTERUPT;
			    System.out.println("Job Execution terminated by server.");
			 }
		    }
		  
		  // Job finished retrieve stderr and stdout from it
		  this.stderr.append(exe.getStderr());
		  this.stdout.append(exe.getStdout());
		  		  
		  // Clean up after the execution
		  exe_thread = null;
		  exe = null;
		  System.gc();
	     
		  i++;
	       }
	  }
	catch ( java.lang.Exception e )
	  {
	     this.exit_value = MIG_JOB_EXIT_ERROR;
	     e.printStackTrace();
	     this.stderr.append( MiG.oneclick.Exception.dumpStackTrace(e) );
	  }
     }
   

   private boolean sendStderr(String send_stderr_url)
     {
	boolean result;
	int stderr_rc;
	HttpsConnection send_conn;
	
	result = true;
	try
	  {
	     // Connect to server
	     send_conn = new HttpsConnection(send_stderr_url, HttpsConnection.PUT );
	     send_conn.open();
	     
	     System.out.println("stderr size: " + this.stderr.length());
	     
	     // write stderr to server
	     send_conn.write(this.stderr.toString());
	     
	     // reset stderr StringBuffer
	     this.stderr.setLength(0);

	     // get responsecode 
	     stderr_rc = send_conn.getResponseCode();
	     if ( stderr_rc != HttpsConnection.HTTP_OK )
	       result = false;
	     
	     /* For Debug
	     System.out.println("RC: " + stderr_rc);
	     readline = send_conn.readLine();
	     while( readline != null )
	       {
		  System.out.println("readline: " + readline);
		  readline = send_conn.readLine();
	       }
	      */
	    
	     send_conn.close();
	  }
	catch ( java.lang.Exception e )
	  {
	     result = false;
	     e.printStackTrace();
	  }
	return result;
     }
   
   private boolean sendStdout(String send_stdout_url)
     {
	boolean result;
	int stdout_rc;
	HttpsConnection send_conn;
	
	result = true;
	try
	  {
	     // Connect to server
	     send_conn = new HttpsConnection(send_stdout_url, HttpsConnection.PUT );
	     send_conn.open();
	     
	     System.out.println("stdout size: " + this.stdout.length());
	     
	     // write stdout to server
	     send_conn.write(this.stdout.toString());
	     
	     // reset stdout StringBuffer
	     this.stdout.setLength(0);
	     
	     // get responsecode 
	     stdout_rc = send_conn.getResponseCode();
	     if ( stdout_rc != HttpsConnection.HTTP_OK )
	       result = false;
	     
	     /* For Debug
	     System.out.println("RC: " + stdout_rc);
	     readline = send_conn.readLine();
	     while( readline != null )
	       {
		  System.out.println("readline: " + readline);
		  readline = send_conn.readLine();
	       }
	      */
	     send_conn.close();
	  }
	catch ( java.lang.Exception e )
	  {
	     result = false;
	     e.printStackTrace();
	  }
	return result;
     }
   
   private boolean sendStatus(String send_status_url)
     {
	boolean result;
	int status_rc;
	HttpsConnection send_conn;
	
	result = true;
	try
	  {
	     // Connect to server
	     send_conn = new HttpsConnection(send_status_url, HttpsConnection.PUT );
	     send_conn.open();
	     
	     System.out.println("exit value: "  + this.exit_value);
	     send_conn.write(String.valueOf(this.exit_value));
	     
	     // get responsecode 
	     status_rc = send_conn.getResponseCode();
	     if ( status_rc != HttpsConnection.HTTP_OK )
	       result = false;
	     
	     /* For Debug
	     System.out.println("RC: " + status_rc);
	     readline = send_conn.readLine();
	     while( readline != null )
	       {
		  System.out.println("readline: " + readline);
		  readline = send_conn.readLine();
	       }
	      */
	     send_conn.close();
	  }
	catch ( java.lang.Exception e )
	  {
	     result = false;
	     e.printStackTrace();
	  }
	return result;
     }
   
      
   private boolean sendJobFinished()
     {
	boolean result;
	
	int i;
	int sendfiles_rc;
		
	String sendfiles_url;
	String send_status_url;
	String send_stderr_url;
	String send_stdout_url;
	String readline;
	
	HttpsConnection sendfiles_conn;

	result = true;
	send_status_url = null;
	send_stderr_url = null;
	send_stdout_url = null;
	
	System.out.println("sendJobFinished");
	// Retrieve information about where to deliver, stderr, stdout  and status
	try
	  {
	     sendfiles_url = this.server + "/sid_redirect/" + this.mig_sessionid + ".sendoutputfiles";
	     System.out.println("sendfiles_url: " + sendfiles_url);
	     
	     sendfiles_rc = HttpsConnection.HTTP_NOT_FOUND;
	     sendfiles_conn = null;
	     while ( sendfiles_conn == null )
	       {
		  sendfiles_conn = new HttpsConnection(sendfiles_url);
		  sendfiles_conn.open();
		  sendfiles_rc = sendfiles_conn.getResponseCode();
		  if ( sendfiles_rc == HttpsConnection.HTTP_NOT_FOUND )
		    {
		       sendfiles_conn.close();
		       sendfiles_conn = null;
		       System.out.println("Failed to retrieve: " + sendfiles_url);
		       Thread.sleep(SEND_JOB_RETRY_TIME);
		    }
	       }
	     readline = sendfiles_conn.readLine();
	     while( readline != null )
	       {
		  //System.out.println("readline: " + readline);
		  if ( readline.indexOf("status: ") == 0 )
		    {
		       send_status_url = readline.substring(readline.indexOf(": ")+2, readline.length());
		    }
		  else if ( readline.indexOf("stderr: ") == 0 )
		    {
		       send_stderr_url = readline.substring(readline.indexOf(": ")+2, readline.length());
		    }
		  else if ( readline.indexOf("stdout: ") == 0 )
		    {
		       send_stdout_url = readline.substring(readline.indexOf(": ")+2, readline.length());
		    }
		  readline = sendfiles_conn.readLine();
	       }
	  }
	catch ( java.lang.Exception e )
	  {
	     result = false;
	     e.printStackTrace();
	  }

	// When status is submitted to server, the job is regarded as finished
	// therefore the last thing send is the status file.
	if (result)
	  result = this.sendStderr(send_stderr_url);
	
	if (result)
	  result = this.sendStdout(send_stdout_url);
	
	if (result)
	  result = this.sendStatus(send_status_url);
		  
	return result;
     }
   
   // Retrieves the files needed and executes the vmplayer 
   public void run()
     {
	this.setStatus( this.INITIALIZING, "Initializing." );
	System.out.println("Resource: " + this.resource_name + ", sandboxkey: " + this.sandboxkey);
	
	do {
	     // Retrieve a new job
	     if ( this.alive && this.retrieveJob() ) 
	     {
		  this.checkjob = new Checkjob(this.server, this.mig_iosessionid);
		  this.checkjob_thread = new Thread(checkjob);
		  this.checkjob_thread.start();
		    
		  // Try to execute the retrieved job
		  this.execute();

		  // Set status msg
		  if (this.alive && this.exit_value != MIG_JOB_EXIT_SERVERINTERUPT) {
		       this.setStatus(this.SENDING_RESULT, "Sending result to server.");
		  
		       // Send status to the MiG-server
		       while ( this.alive && this.checkjob.jobActive() && !this.sendJobFinished() ) {
			    try {
				 System.out.println("SendJobFinished  failed, trying again later.");
				 Thread.sleep(SEND_JOB_RETRY_TIME);
			      }
			    catch( java.lang.Exception e ) {e.printStackTrace();}
			 }
		    }
		  
		  if (this.alive) {
		       if ( this.exit_value == MIG_JOB_EXIT_OK )
			 this.jobs_done++;
		       else
			 this.jobs_failed++;
		    }
		  this.setStatus(this.JOB_FINISHED, "Job Finished.");
		  if (this.checkjob_thread.isAlive())
		    this.checkjob_thread.stop();
	       }
	     else if (this.alive) {
		  this.setStatus(this.FAILED, "Job retrieve failed.");
		  System.out.println("Failed to retrieve job.");
	       }
	     
	     if (this.alive) {
		  try {
		       System.out.println("Resource loop finished, sleep for a while");
		       Thread.sleep(1000);
		    }
		  catch( java.lang.Exception e ) {e.printStackTrace();}
		  //System.out.println("Oneshot: " + this.oneshot);
	       }
	  } while(!this.oneshot && this.alive);
     }
}

 
