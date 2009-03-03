/*
# Job - OneClick resource job framework
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
  
import java.lang.StringBuffer;
import java.util.Vector;

import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.io.ObjectOutputStream;
import java.net.URL;
import javax.net.ssl.HttpsURLConnection;

/** This class provides the framework needed to create a MiGOneClick job.
 *
 * @author Martin Rehr
 * @version 0.1 Oct 4, 2006.
 */

public abstract class Job implements java.io.Serializable
{
   private int checkpoint_id;
   private String server;
   private String iosessionid;
   private String jobid;
   private StringBuffer stderr;
   private StringBuffer stdout;
   private Vector files;
   private Thread MiG_job_thread;
   
   /** The main method of the MiGOneClick job.
    * 
    * @param argv                  Array of arguments given to the MiGOneClick job.
    */
   public abstract void MiG_main(String[] argv);
   
   protected Job()
     {
	this.checkpoint_id = 0;
	this.server = null;
	this.iosessionid = null;
	this.jobid = null;
	this.stderr = new StringBuffer();
	this.stdout = new StringBuffer();
	this.files = new Vector();
     }

   private void cleanup_filelist()
     {
	int i;
	int j;
	File file;
	File file2;
	
	for (i=0; i<this.files.size(); i++) {
	   file = (File) this.files.elementAt(i);
	   if (file.getMode() == File.CLOSED && file.getFlushCount() == 0) {
	      System.out.println("Removing: " + i + " : " + file.getFilename());
	      this.files.removeElementAt(i);
	      i--;
	   }
	   else if (file.getFlushCount() > 0) {
	      for (j=0; j<this.files.size(); j++) {
		 file2 = (File) this.files.elementAt(j);
		 if (file != file2 && file.getFilename().compareTo(file2.getFilename()) == 0) {
		    this.files.removeElementAt(j);
		    System.out.println("Removing dublee: " + j + " : " + file.getFilename());
		    j--;
		 }
	      }
	   }
	}
     }
   	
   
   /** Used for creating a new checkpoint
    *
    */
   protected boolean checkpoint()
     {
	boolean result;
	int http_rc;
	int i;
	
	String checkpoint_name;
	String checkpoint_url_str;
	MiG.oneclick.File file;
	URL url;
	HttpsURLConnection httpsUrlConn;
	ObjectOutputStream oos;
	OutputStreamWriter osw;
	
	this.checkpoint_id++;

	try
	  {
	     // Checkpoint associated filed
	     this.cleanup_filelist();
	       
	     for (i=0; i<this.files.size(); i++)
	       {
		  file = (File) this.files.elementAt(i);
		  if (file.getFlushCount() > 0)
		    {
		       checkpoint_name = this.jobid + "." + file.getFilename() + ".checkpoint." + this.checkpoint_id;
		       checkpoint_url_str = this.server + "/cgi-sid/cp.py?iosessionid=" + this.iosessionid 
	                                                                 + "&src=" + file.getFilename()
	                                                                 + "&dst=" + checkpoint_name;

		       System.out.println("checkpoint_url_str: " + checkpoint_url_str);
		       url = new URL(checkpoint_url_str);
		       
		       httpsUrlConn = (HttpsURLConnection) url.openConnection();
		       httpsUrlConn.setRequestMethod("GET");
		       httpsUrlConn.connect();
		       
		       http_rc = httpsUrlConn.getResponseCode();
		       
		       System.out.println("New File checkpoint: '" + file.getFilename() + "', rc: " + http_rc);
		       httpsUrlConn.disconnect();
		    }
	       }
	     
	     
	     // Write the job as a java object to MiG server
	     checkpoint_url_str = this.server + "/sid_redirect/" + this.iosessionid + "/";  
	     checkpoint_name = this.jobid + "." + this.getClass().getName() + ".checkpoint";

	     url = new URL(checkpoint_url_str + checkpoint_name +  "." + this.checkpoint_id);
	     
	     httpsUrlConn = (HttpsURLConnection) url.openConnection();
	     httpsUrlConn.setRequestMethod("PUT");
	     httpsUrlConn.setDoOutput(true);
	     httpsUrlConn.connect();
	     
	     oos = new ObjectOutputStream(httpsUrlConn.getOutputStream());
	     oos.writeObject(this);
	     oos.flush();
	     
	     http_rc = httpsUrlConn.getResponseCode();
	     httpsUrlConn.disconnect();
	     
	     // Write active checkpoint to MiG server, this is done to confirm that checkpoint was successfully written.
	     url = new URL(checkpoint_url_str + checkpoint_name + ".latest");
	     
	     httpsUrlConn = (HttpsURLConnection) url.openConnection();
	     httpsUrlConn.setRequestMethod("PUT");
	     httpsUrlConn.setDoOutput(true);
	     httpsUrlConn.connect();
	     
	     osw = new OutputStreamWriter(httpsUrlConn.getOutputStream());
	     osw.write(String.valueOf(this.checkpoint_id));
	     osw.flush();
	     
	     httpsUrlConn.disconnect();
	     http_rc = httpsUrlConn.getResponseCode();
	     System.out.println("New object checkpoint, rc: " + http_rc);
	     result = true;
	  }
	catch (java.lang.Exception e)
	  {
	     result = false;
	     e.printStackTrace();
	  }
	return result;
     }
   
   /** Used for restoring files from checkpoint
    *
    */
   public boolean restoreCheckpointedFiles()
     {
	boolean result;
	int http_rc;
	int i;
	
	String checkpoint_name;
	String checkpoint_url_str;
	MiG.oneclick.File file;
	URL url;
	HttpsURLConnection httpsUrlConn;
	
	result = false;
	
	try
	  {
	     for (i=0; i<this.files.size(); i++)
	       {
		  file = (File) files.elementAt(i);
		  
		  // Set iosessionid for this job
		  if (file.getMode() != File.CLOSED)
		    file.setIOsessionid(this.iosessionid);
					
		  if (file.getFlushCount() > 0)
		    {
		       /*
		       // Remove original file
		       checkpoint_name = this.jobid + "." + file.getFilename() + ".checkpoint." + this.checkpoint_id;
		       checkpoint_url_str = this.server + "/cgi-sid/rm.py?iosessionid=" + this.iosessionid 
			                                                                + "&path=" + file.getFilename();
		  
		       System.out.println("restore checkpoint_url_str: " + checkpoint_url_str);
		       url = new URL(checkpoint_url_str);
		  
		       httpsUrlConn = (HttpsURLConnection) url.openConnection();
		       httpsUrlConn.setRequestMethod("GET");
		       httpsUrlConn.connect();
		       http_rc = httpsUrlConn.getResponseCode();
		       
		       System.out.println("Restore File checkpoint remove: '" + file.getFilename() + "', rc: " + http_rc);
		       httpsUrlConn.disconnect();
		       */
		       // Copy checkpointed file to orginal file
		       checkpoint_name = this.jobid + "." + file.getFilename() + ".checkpoint." + this.checkpoint_id;
		       checkpoint_url_str = this.server + "/cgi-sid/cp.py?iosessionid=" + this.iosessionid 
			                                                                + "&src=" + checkpoint_name
			                                                                + "&dst=" + file.getFilename();
		  
		       System.out.println("restore checkpoint_url_str: " + checkpoint_url_str);
		       url = new URL(checkpoint_url_str);
		  
		       httpsUrlConn = (HttpsURLConnection) url.openConnection();
		       httpsUrlConn.setRequestMethod("GET");
		       httpsUrlConn.connect();
		       http_rc = httpsUrlConn.getResponseCode();
		       
		       System.out.println("Restore File checkpoint copy: '" + file.getFilename() + "', rc: " + http_rc);
		       httpsUrlConn.disconnect();
		    }
	       }
	     	result = true;
	  }
	catch (java.lang.Exception e)
	  {
	     result = false;
	     e.printStackTrace();
	  }
	return result;
     }
   
   /** Used to get the checkpoint counter.
    *     * @return The checkpoint counter as int.
    *     */
   public int getCheckpointID()
     {
	return this.checkpoint_id;
     }
   
   
   /** Used for writing to the MiG job stderr.
    * 
    * @param str                   String containing the stderr message.
    */
   protected void err(String str)
     {
	this.stderr.append(str);
     }
   
   /** Used for writing to the MiG job stdout.
    * 
    * @param str                   String containing the stdout message.
    */
   protected void out(String str)
     {
	this.stdout.append(str);
     }
   
   /** Used for retrieving a {@link MiG.oneclick.File} object, containing information required to perform file I/O.
    * @return {@link MiG.oneclick.File} containing the MiG server URL and job iosessionid needed to perform the file I/O.
    */
   protected MiG.oneclick.File open_file(String filename, int mode) throws MiG.oneclick.FileException
     {
	boolean status;
	  
	MiG.oneclick.File file;
	
	System.out.println("Opening file: '" + filename + "' in mode: " + mode);
	file = new MiG.oneclick.File(this.server, this.iosessionid, filename, mode);
	
	if (file.getMode() == mode)
	  this.files.addElement(file);
	else
	  throw new MiG.oneclick.FileException(file.getErrorMessages());
	    
	return file;
     }

   /** Used for setting the information about the job, this is set by the executing framework, and should not be altered.
    * @param server                String containing the MiG server URL.
    * @param iosessionid             String containing the MiG iosessionid of the job.
    */
   public void setInfo( String server, String iosessionid, String jobid )
     {
	this.server = server;
	this.iosessionid = iosessionid;
	this.jobid = jobid;
     }
   
   /** Used for retrieving the id of the job
    * @return String containing MiG jobid
    */
   protected String getJobid()
     {
	return this.jobid;
     }

    /** Used for retrieving the MiG iosessionid
    * @return String containing MiG iosessionid
    */
   protected String getIOsessionid()
     {
	return this.iosessionid;
     }

   /** Used to get the MiG job stderr.
    * @return StringBuffer containing the MiG job stderr.
    */
   public StringBuffer getStderr()
     {
	return this.stderr;
     }
   
   /** Used to get the MiG job stdout.
    * @return StringBuffer containing the MiG job stdout.
    */
   public StringBuffer getStdout()
     {
	return this.stdout;
     }
}


 
