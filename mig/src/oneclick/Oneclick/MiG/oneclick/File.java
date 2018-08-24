/*
# File - OneClick resource file access wrapper
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
import java.net.URL;
import java.io.*;
import java.util.Vector;

/** This class provides fileaccess for the MiGOneClick framework.
 *
 * @author Martin Rehr
 * @version 0.1 Oct 4, 2006.
 */

public class File implements java.io.Serializable
{
   // Buffer and blocksize konstants
   private final static int MAX_INT = 0xFFFF;
      
   // Test Constants
   //private final static int BUFFERSIZE = 8388608;
   //private final static int INIT_BLOCKSIZE = 2048;
   //private final static double BS_BW_CUTOFF_RATIO = 1.70;
   //private final static double INIT_BS_BW = 1.0;
   
   // Production Constants
   private final static int BUFFERSIZE = 1048576;
   private final static int INIT_BLOCKSIZE = 2048;
   private final static double INIT_BS_BW = 1.0;
   private final static double BS_BW_CUTOFF_RATIO = 1.65;
   
   // For Test
   //private final static int BUFFERSIZE = 10485760;
   //private final static double BS_BW_CUTOFF_RATIO = 1.75;
   //public double BS_BW_CUTOFF_RATIO = 0;
   
   // HTTP returncodes
   private final static int HTTP_OK = 200;
   private final static int HTTP_CREATED = 201;
   private final static int HTTP_FORBIDDEN = 403;
   private final static int HTTP_NOT_FOUND = 404;
   private final static int HTTP_CONFLICT = 409;
   private final static int HTTP_RANGE_NOT_SATISFIABLE = 416;

   // MiG CGI returncodes
   private final static int MIG_CGI_OK = 0;
   private final static int MIG_CGI_ERROR = 1;
   
   // File is CLOSED
   public final static int CLOSED = -1;
      
   /** Used to open file in mode READ
    */
   public final static int R = 0;
   
   /** Used to open file in mode WRITE (File is truncated)
    */
   public final static int W = 1;

   /** Used to open file in mode UPDATE
    */
   public final static int WW = 2;
   
   /** Used to open file in mode READ/WRITE (File is truncated)
    */
   public final static int RW = 3;
   
   /** Used to open file in mode READ/UPDATE
    */
   public final static int RWW = 4;
  
   private int mode;
   private int bufferpos;
   private int bufferend;
   private int blocksize;
   private int new_blocksize;
   private int flushcount;
   private long filepos;
   private double last_bs_bw;
   private byte[] buffer;
   private boolean disable_https_trustmanager;
   private String filename;
   private String server;
   private String iosessionid;
   private String read_url;
   private String write_url;
   private String delete_url;
   private StringBuffer error_messages;
   private Vector[] transferlog;
   
   /** Creates a File object.
    * @param server                  URL to the server containing the files to access.
    * @param iosessionid               The MiG iosessionid.
    */
   public File(String server, String iosessionid, String filename, int mode)
     {
	this.init(server, iosessionid, filename, mode, false);
     }
   
   /** Creates a File object, possible without a trustmanager.
    * @param server                      URL to the MiG server containing the files to access.
    * @param iosessionid                   The MiG iosessionid.
    * @param disable_https_trustmanager  If true, this disables the https trustmanager, this is needed if the server uses a non-authorized https certificate.
    */
   public File(String server, String iosessionid, String filename, int mode, boolean disable_https_trustmanager)
     {
	System.out.println("Tes2: " + mode);
	this.init(server, iosessionid, filename, mode, disable_https_trustmanager);
     }

  
   private void init(String server, String iosessionid, String filename, int mode,  boolean disable_https_trustmanager)
     {
	this.server = server;
	this.iosessionid = iosessionid;
	this.filename = filename;
	
	this.filepos = 0;
	this.bufferpos = 0;
	this.bufferend = 0;
	this.flushcount = 0;
	this.blocksize = File.INIT_BLOCKSIZE;
	this.new_blocksize = 0;
	this.last_bs_bw = File.INIT_BS_BW;
		
	this.mode = File.CLOSED;
	this.disable_https_trustmanager = disable_https_trustmanager;
	this.transferlog = null;
	this.buffer = new byte[this.BUFFERSIZE];
	this.error_messages = new StringBuffer();

	try
	  {
	     // Create read and write urls for datatransmission
	     this.setURLS();
	     
	     // Create new file if needed.
	     if ( mode == File.W || mode == File.RW )
	       {
		  this.createFile();
	       }
	     
	     // Fetch the first 'this.blocksize' bytes form the file, if in any read mode.
	     if ( mode != File.W && mode != File.WW )
	       {
		  this.fetch();
	       }
	     this.mode = mode;
	  }
	catch (java.lang.Exception e)
	  {
	     this.mode = File.CLOSED;
	     this.addErrorMessage("File:open() -> " + e + "\n" 
				  + MiG.oneclick.Exception.dumpStackTrace(e));
	  }
     }
   
   private void setURLS()
     {
	// Create read url
	this.read_url = this.server + "/cgi-sid/rangefileaccess.py?iosessionid=" + this.iosessionid + "&filename=" + this.filename;
	
	// Create write url
	this.write_url = this.server + "/cgi-sid/rangefileaccess.py?iosessionid=" + this.iosessionid + "&filename=" + this.filename;
	
	// Create delete url
	this.delete_url = this.server + "/cgi-sid/rm.py?iosessionid=" + this.iosessionid + "&path=" + this.filename;
     }
   
   
   // Create file, done by first deleting old file, and then creating empty file.
   private void createFile() throws java.lang.Exception
     {
	int http_rc;
	int cgi_rc;
	
	HttpsConnection httpsConn;

	// Remove file if exists
	httpsConn = new HttpsConnection(this.delete_url, HttpsConnection.GET, this.disable_https_trustmanager );
	httpsConn.open();
		     
	http_rc = httpsConn.getResponseCode();
	if ( http_rc != File.HTTP_OK )
	  {
	     throw new FileException("createFile(): delete recieved HTTP returncode: " + http_rc);
	  }
	
	httpsConn.close();
	
	// Create a new file
	httpsConn = new HttpsConnection(this.write_url, HttpsConnection.PUT, this.disable_https_trustmanager );
	httpsConn.open();
	http_rc = httpsConn.getResponseCode();
	
	// The custom python http server would reply this: if File.HTTP_CREATED 
	// The cgi-sid/put framework replys this File.HTTP_OK   
	
	if ( http_rc != File.HTTP_OK )
	  {
	     throw new FileException("createFile(): create recieved HTTP returncode: " + http_rc);
	  }

	cgi_rc = Integer.parseInt( httpsConn.readLine() );
	if ( cgi_rc != MIG_CGI_OK )
	  {
	     throw new FileException("createFile(): recieved MIG_CGI returncode: " + cgi_rc);
	  }
     	  
	httpsConn.close();
     }
   
   private void updateBlockSize(long starttime, long endtime, int num_of_bytes)
     {
	double current_bs_bw;
	long elapsedtime;
	
	elapsedtime = endtime - starttime;
	
	if ( elapsedtime > 0 )
	  {
	     current_bs_bw = num_of_bytes/elapsedtime;
	  }
	else
	  {
	     current_bs_bw = num_of_bytes;
	  }
	
	if ( this.transferlog != null )
	  {
	     this.transferlog[0].addElement(Integer.toString(this.blocksize));
	     this.transferlog[1].addElement(Long.toString(elapsedtime));
	     this.transferlog[2].addElement(Integer.toString(num_of_bytes));
	     this.transferlog[3].addElement(Double.toString(current_bs_bw));
	     this.transferlog[4].addElement(Double.toString(current_bs_bw/this.last_bs_bw));
	  }
	
	
	if ( this.blocksize < BUFFERSIZE 
	     &&
	     current_bs_bw/this.last_bs_bw >= BS_BW_CUTOFF_RATIO )
	  {
	     /*
	     System.out.println("\nfile: " + this.filename);
	     System.out.println("BS_BW_CUTOFF_RATIO: " + BS_BW_CUTOFF_RATIO);
	     System.out.println("elapsed: " + elapsedtime);
	     System.out.println("last_bw: " + this.last_bs_bw);
	     System.out.println("current_bw: " + current_bs_bw);
	     System.out.println("current_bw/last_bw: " + (current_bs_bw/this.last_bs_bw));
	     System.out.println("current_blocksize: " + this.blocksize);
	     System.out.println("num_of_bytes: " + num_of_bytes);
	     */
	     this.new_blocksize = this.blocksize*2;
	     this.last_bs_bw = current_bs_bw;
	     
	     //System.out.println("new_blocksize: " + this.new_blocksize);
	  }
	/*
	else
	  {
	     System.out.println("\nfile: " + this.filename);
	     System.out.println("BS_BW_CUTOFF_RATIO: " + BS_BW_CUTOFF_RATIO);
	     System.out.println("elapsed: " + elapsedtime);
	     System.out.println("last_bw: " + this.last_bs_bw);
	     System.out.println("current_bw: " + current_bs_bw);
	     System.out.println("current_bw/last_bw: " + (current_bs_bw/this.last_bs_bw));
	     System.out.println("current_blocksize: " + this.blocksize);
	     System.out.println("num_of_bytes: " + num_of_bytes);
	  }
	 */
	
     }
   
   private void addErrorMessage(String error_message)
     {
	this.error_messages.append("\n================= Begin message =================\n");
	this.error_messages.append(error_message);
	this.error_messages.append("\n================== End Message ==================\n");
     }
   
   // Retrieves data from read_url.
   private void fetch() throws java.lang.Exception
     {
	// java uses int for unsigned byte (stupid)
	int bytesread;
	int http_rc;
	int cgi_rc;
	long starttime;
	long endtime;
	
	String fetch_url;
	HttpsConnection httpsConn;

	// if blocksize updated, activate new block size
	if ( this.blocksize < this.new_blocksize )
	  {
	     this.blocksize = this.new_blocksize;
	  }
	
	// This is for setting range parameters to the cgi-sid/rangefileaccess script to use for reading.
	fetch_url = this.read_url
	               + "&file_startpos=" + this.filepos 
	               + "&file_endpos=" + (this.filepos + this.blocksize-1);
	
	//System.out.println("fetch_url: " + fetch_url);
	
	// Open conenction to read_url.
	httpsConn = (HttpsConnection) new HttpsConnection(fetch_url, this.disable_https_trustmanager);
	
	// Start time messure
	starttime = System.currentTimeMillis();

	// Connect to read_url
	httpsConn.open();

	// Get responsecode from server
	http_rc = httpsConn.getResponseCode();

	// The cgi-sid/rangefileaccess framework reply this: 
	// HTTP responsecode: HTTP_OK everytime.
	// char: '0', if everything went ok
	// char: '1', if something went wrong.
	if ( http_rc != File.HTTP_OK )
	  {
	     httpsConn.close();
	     throw new FileException("fetch recieved HTTP returncode: " + http_rc);
	  }

	// Httpconnection went ok, reset bufferend, 
	// as cgi failure is due to fetch out of range
	// and we need to reset it before filling with data
	this.bufferend = 0;

	cgi_rc = Integer.parseInt( httpsConn.readLine() );
	if ( cgi_rc != MIG_CGI_OK )
	  {
	     httpsConn.close();
	     throw new FileException("fetch recieved MIG_CGI returncode: " + cgi_rc);
	  }
	  	
	// We got the data, fill the buffer
	bytesread = httpsConn.read(this.buffer, 0, this.blocksize);
	while ( bytesread != -1 && this.blocksize-this.bufferend > 0 )
	  {
	     this.bufferend = this.bufferend + bytesread;
	     bytesread = httpsConn.read(this.buffer, this.bufferend, this.blocksize-this.bufferend);
	  }
		
	// Disconnect 
	httpsConn.close();
	
	// End Time messure	    
	endtime = System.currentTimeMillis();
	
	// Update blocksize	   
	this.updateBlockSize(starttime, endtime, this.bufferend);
	
	// Reset bufferpos.
	this.bufferpos = 0;
	
	//System.out.println("this.bufferend: " + this.bufferend);
     }
   
   
   
   /** Reads the next byte of data from the file.
    * @return                      -1 if EOF is reached or something went wrong.
    *                              If something went wrong the {@link #getErrorMessages} method can be used to 
    *                              retrieve information on what happend.
    *                              Actual data is returned as a value 0-255, 
    *                              the 'rocket scientist' who defined java's primitive
    *                              types did'nt find any use for signed types.
    *                              Therefor we are forced to use the first 8 bit of a int to simulate
    *                              a signed byte.
    */
   
   // Reads data from local buffer, and fetches new buffer if required.
   // Returns value 0-255, the *rocket scientist* who defined java's primitive
   // types did'nt find any use for signed types ( What a lamer ),
   // therefor we are forced to use the first 8 bit of a int to simulate
   // a signed byte.
   public int read()
     {
	int result;
	result = -1;
	
	try
	  {
	     // Check if file is opened for read
	     if ( this.mode == File.CLOSED )
	       {
		  throw new FileException("File is CLOSED!");
	       }
	     
	     if ( this.mode == File.W || this.mode == File.WW )
	       {
		  throw new FileException("File is not opened for READ!");
	       }
	     
	     // If our buffer ran out of data, fetch a new chunck from read_url.
	     if ( this.bufferpos == this.blocksize )
	       {
		  if ( this.mode != File.R )
		    {
		       if (!this.flush())
			 {
			    throw new FileException("Flush FAILED!");
			 }
		    }
		  else
		    {
		       // Flush sets this.filepos after data has been written to the server.
		       // If we dont flush, we increase filepos here.
		       this.filepos = this.filepos + this.blocksize;
		    }
		  this.fetch();
	       }
		  
	     // Return next byte in buffer.
	     if ( this.bufferpos < this.bufferend )
	       {
		  result = (int) (this.buffer[this.bufferpos] & 0x00FF);
		  this.bufferpos++;
	       }
	  }
	catch (java.lang.Exception e)
	  {
	     result = -1;
	     this.addErrorMessage("File:read() -> " + e + "\n"
	                          + MiG.oneclick.Exception.dumpStackTrace(e) );
	  }
	
	return result;
     }

   /** Flushes a file opened for write to the MiG server. 
    * @return                      boolean indicating if everyting went ok. If false is
    *                              returned a message describing the error can be retrieved by 
    *                              the {@link #getErrorMessages} method.
    */
   public boolean flush()
     {
	boolean status;
	int http_rc;
	int cgi_rc;
	long starttime;
	long endtime;
	
	String flush_url;
	HttpsConnection httpsConn;
	
	status = false;
	
	try
	  {
	     if (this.mode == File.CLOSED)
	       {
		  throw new FileException("File is CLOSED.");
	       }
	     if (this.mode == File.R)
	       {
		  throw new FileException("File is not opened for WRITE!");
	       }
	     
	     if ( this.bufferpos == 0 )
	       {
		  // Nothing to flush
		  status = true;
	       }
	     else
	       {
		  // This is for setting range parameters to the cgi-sid/rangefileaccess script to use for writing.
		  // We only write to bufferpos-1, as bufferpos is the next point where the buffer can get modified.
		  // Note that every seek invokes a flush or a fetch or both, and thereby resets bufferpos.
		  flush_url = this.write_url
		            + "&file_startpos=" + this.filepos 
		            + "&file_endpos=" + (this.filepos + this.bufferpos-1);
		  
		  //System.out.println("flush_url: " + flush_url);
		  
		  // Creat httpsConn
		  httpsConn = new HttpsConnection(flush_url, HttpsConnection.PUT, this.disable_https_trustmanager);
		  
		  // This is used by the custom http server, for Range puts
		  //httpsConn.setRequestProperty("Range", "bytes=" + this.filepos + "-" + (this.filepos + this.bufferpos-1));
		  
		  // Start time messure
		  starttime = System.currentTimeMillis();
		  
		  // Connect to flush_url
		  httpsConn.open();
		  
		  // Send data
		  httpsConn.write(this.buffer,0, this.bufferpos);
		  
		  // Get the server response code of the PUT.
		  http_rc = httpsConn.getResponseCode();
		  
		  // The cgi-sid/rangefileaccess framework reply this: 
		  // HTTP responsecode: HTTP_OK everytime.
		  // char: '0', which equals int: 48 to stdout if everything went ok
		  // char: '1', which equals int: 49 to stdout if something went wrong.
		  if ( http_rc != File.HTTP_OK )
		    {
		       throw new FileException("flush recieved HTTP returncode: " + http_rc);
		    }
		  
		       cgi_rc = Integer.parseInt( httpsConn.readLine() );
		  if ( cgi_rc != MIG_CGI_OK )
		    {
		       throw new FileException("flush recieved MIG_CGI returncode: " + cgi_rc);
		    }
		  
		  // Close connection.
		  httpsConn.close();
		  
		  // End time messure
		  endtime = System.currentTimeMillis();
		  
		  // Update blocksize
		  this.updateBlockSize(starttime, endtime, this.bufferpos);
		       
		  // if blocksize updated, activate new block size
		  if ( this.blocksize < this.new_blocksize )
		    {
		       this.blocksize = this.new_blocksize;
		    }
		  
		  // Update filepos and reset buffer pos.
		  this.filepos = this.filepos + this.bufferpos;
		  this.bufferpos = 0;
		  this.bufferend = 0;
		  
		  // Increment flush count
		  this.flushcount++;
		  status = true;
	       }
	  }
	catch (java.lang.Exception e)
	  {
	     status = false;
	     this.addErrorMessage("File:flush() -> " + e + "\n"
				  + MiG.oneclick.Exception.dumpStackTrace(e) );
	  }
	return status;
     }
   

   
    /** Writes a byte to the file, see {@link #read()} for describtion of why the byte is represented as an int.
    * @return                      boolean indicating the status of the write.
    *                              If something went wrong the {@link #getErrorMessages} method can be used to 
    *                              retrieve information on what happend.
    *                              
    */
   
   // Write to an open file.
   // Writes value 0-255 of the given int.
   // The *rocket scientist* who defined java's primitive
   // types did'nt find any use for signed types ( What a lamer ),
   // therefor we are forced to use the first 8 bit of a int to simulate
   // a signed byte.
   public boolean write(int b) 
     {
	boolean status;
	status = false;
	
	try
	  {
	     // Check if file is opend in WRITE mode
	     if ( this.mode == File.CLOSED )
	       {
		  throw new FileException("File is CLOSED!");
	       }
	     
	     if ( this.mode == File.R )
	       {
		  throw new FileException("File is not opened for WRITE!");
	       }
	     
	     // Check if buffer is full, if so flush it.
	     if ( this.bufferpos == this.blocksize )
	       {
		  if (!this.flush())
		    {
		       throw new FileException("Flush FAILED!");
		    }
		  		  
		  // If the file is opened in any Read/Write mode, fetch buffer before writing to it.
		  if ( this.mode != File.W && this.mode != File.WW )
		    {
		       this.fetch();
		    }
	       }
	     
	     // Write byte to buffer, HI 8 bits of int is discarded
	     this.buffer[this.bufferpos] = (byte) (b & 0x00FF);
	     
	     // Update buffer position.
	     this.bufferpos++;
	     
	     status = true;
	  }
	
	catch (java.lang.Exception e)
	  {
	     status = false;
	     this.addErrorMessage("File:write(int b) -> " + e + "\n"
	                          + MiG.oneclick.Exception.dumpStackTrace(e));
	  }
	return status;
     }

    /** Seeks to the specified position in the file.
     * @param newfilepos           Indicating the new fileposition relativly to the beginning of the file.
     * @return                     boolean indicating the status of the seek.
     *                             If something went wrong the {@link #getErrorMessages} method can be used to 
     *                             retrieve information on what happend.
    */
   public boolean seek( long newfilepos )
     {
	boolean status;
	status = false;
	
	try
	  {
	     // Check if file is closed.
	     if ( this.mode == File.CLOSED )
	       {
		  throw new FileException("File is CLOSED!");
	       }
	     
	     // If file is opened in any WRITE mode, flush before seek.
	     if ( this.mode != File.R )
	       {
		  if (!this.flush())
		    {
		       throw new FileException("Flush FAILED!");
		    }
		  this.filepos = newfilepos;
	       }
	     
	     // If file is opened in any READ mode, fetch data after the new filepos is set.
	     if ( this.mode != File.W && this.mode != File.WW )
	       {
		  this.filepos = newfilepos;
		  try {
		     this.fetch();
		  }
		  catch ( FileException e )
		    {
		       // It's ok to get this exception, 
		       // as the file is checked for existance at open
		       // its only out of range that is possible, and
		       // it is allowed to seek out of range.
		       // Maybe a FileOutOfRange Exception should be made.
		    }
	       }
	     
	     status = true;
	  }
	catch (java.lang.Exception e)
	  {
	     status = false;
	     this.addErrorMessage("File:seek(long n) -> " + e + "\n"
	                          + MiG.oneclick.Exception.dumpStackTrace(e));
	  }
	return status;
     }
   
   /** Closes the file, if the file is opened in write mode a {@link #flush()} is invoked.
    * @return                     boolean indicating the status of the close.
    *                             If something went wrong the {@link #getErrorMessages} method can be used to 
    *                             retrieve information on what happend.
    */
   public boolean close()
     {
	boolean status;
	status = false;
	
	try
	  {
	     // Check if file is allready closed.
	     if ( this.mode == File.CLOSED )
	       {
		  throw new FileException("File is allready CLOSED!");
	       }
	     
	     // If file is opened in any WRITE mode, flush on close.
	     if ( this.mode != File.R )
	       {
		  if (!this.flush())
		    {
		       throw new FileException("Flush FAILED!");
		    }
	       }
	     this.mode = File.CLOSED;
	     this.buffer = null;
	     this.error_messages = null;
	     this.transferlog = null;
	     status = true;
	  }
	catch (java.lang.Exception e)
	  {
	     status = false;
	     this.addErrorMessage("File:close() -> " + e + "\n"
	                          + MiG.oneclick.Exception.dumpStackTrace(e));
	  }
	return status;
     }

   /** Changes the session of an allready opend file.
    *  Used with checkpointing of opend files
    */
   public void setIOsessionid(String iosessionid)
     {
	this.iosessionid = iosessionid;
	
	// Create read and write urls for new iosessionid
	this.setURLS();
     }
   
   /** Returns the mode in which the file was opend
    */
   public int getMode()
     {
	return this.mode;
     }

   /** Returns the filename of the file.
    */
   public String getFilename()
     {
	return this.filename;
     }

   /** Returns the number of flushes performed on this file.
    */
   public int getFlushCount()
     {
	return this.flushcount;
     }
      
   /** Starts logging of the Transferrates
    */
   public void startTransferLogging()
     {
	this.transferlog = new Vector[5];
	// Blocksize
	this.transferlog[0] = new Vector();
	
	// Transfertime
	this.transferlog[1] = new Vector();
	
	// Bytes transfered
	this.transferlog[2] = new Vector();
	
	// Bandwidth
	this.transferlog[3] = new Vector();
	
	// Bandwidth ratio
	this.transferlog[4] = new Vector();
     }

   /** Returns the transferlog
    */
   public Vector[] getTransferLog()
     {
	return this.transferlog;
     }
   
   
   /** Clears the File ErrorMessage buffer.
    */
   public void resetErrorMessages()
     {
	this.error_messages.setLength(0);
     }
   
   /** Returns the ErrorMessage buffer as a String.
    */
   public String getErrorMessages()
     {
	return this.error_messages.toString();
     }

   /** For DEBUG
    */
   public int getBlockSize() 
     {
	return this.blocksize;
     }
} 
 
