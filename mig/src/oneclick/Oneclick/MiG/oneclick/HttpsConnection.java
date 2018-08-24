/*
# HttpsConnection - OneClick server connection wrapper 
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

import java.io.InputStreamReader;
import java.io.BufferedReader;
import java.io.BufferedInputStream;
import java.io.OutputStreamWriter;
import java.io.BufferedWriter;
import java.io.BufferedOutputStream;

import java.net.URL;

import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.TrustManager;
import javax.net.ssl.SSLContext;
import javax.net.ssl.X509TrustManager;



//import java.net.*;
//import javax.net.ssl.*;
//import java.security.*;

public class HttpsConnection
{
   public final static int HTTP_OK = 200;
   public final static int HTTP_NOT_FOUND = 404;

   public final static int MIG_CGI_OK = 0;
   public final static int MIG_CGI_ERROR = 1;
   

   public final static int GET = 1;
   public final static int PUT = 2;
   public final static int DELETE = 3;

   public final static int EOS = -1;
   public final static int NEWLINE = 10;
   
   private boolean disable_trustmanager;
   private int content_length;
   private int request_method;
   
   private URL url;
   private HttpsURLConnection httpsUrlConn;
   private BufferedReader BR;
   private BufferedWriter BW;
   private BufferedInputStream BI;
   private BufferedOutputStream BO;
   
      
   public HttpsConnection(String url_string) throws java.lang.Exception
     {
	this.init(url_string, GET, false);
     }
   
   public HttpsConnection(String url_string, int request_method ) throws java.lang.Exception
     {
	this.init(url_string, request_method, false);
     }
   
   public HttpsConnection(String url_string, boolean disable_trustmanager) throws java.lang.Exception
     {
	this.init(url_string, GET, disable_trustmanager);
     }
   
   public HttpsConnection(String url_string, int request_method, boolean disable_trustmanager) throws java.lang.Exception
     {
	this.init(url_string, request_method, disable_trustmanager);
     }
   	  
   private void init(String url_string, int request_method, boolean disable_trustmanager) throws java.lang.Exception
     {
	this.url = new URL(url_string);
	this.request_method = request_method;
	this.disable_trustmanager = disable_trustmanager;
	this.httpsUrlConn = null;
	this.BR = null;
	this.BW = null;
	this.BO = null;
	
	// If the connection is from an applet, 
	// the applet codebase must be located at a https connection,
	// and thereby the SSL auth is done by the browser.
	// If the connection is _NOT_ from an applet, we tell java
	// to accept connections to all servers without the use of a keystore file.
	if ( this.disable_trustmanager )
	  {
	     SSLContext sc;
	     
	     //// Install the all-trusting trust manager
	     sc = SSLContext.getInstance("SSL");
	     sc.init(null, this.getTrustManager(), new java.security.SecureRandom());
	     HttpsURLConnection.setDefaultSSLSocketFactory(sc.getSocketFactory());
	  }
	
	// Create httpsURLConnection. 
	this.httpsUrlConn = (HttpsURLConnection) this.url.openConnection();
	if ( this.request_method == PUT )
	  {
	     this.httpsUrlConn.setRequestMethod("PUT");
	     this.httpsUrlConn.setDoOutput(true);
	  }
	else if ( this.request_method == DELETE )
	  {
	     this.httpsUrlConn.setRequestMethod("DELETE");
	  }
     }
      
   
   // This trustmanager allows connections to all https, regardless of their certificate.
   private TrustManager[] getTrustManager()
     {
	return new TrustManager[]{
	   new X509TrustManager() {
	      public java.security.cert.X509Certificate[] getAcceptedIssuers() 
		{
		   return null;
		}
	      public void checkClientTrusted(java.security.cert.X509Certificate[] certs, String authType) 
		{
		}
	      public void checkServerTrusted(java.security.cert.X509Certificate[] certs, String authType) 
		{
		}
	   }
	};
     }

   private void flush() throws java.lang.Exception
     {
	if (this.BW != null)
	  {
	     this.BW.flush();
	  }
	
	if (this.BO != null)
	  {
	     this.BO.flush();
	  }
     }
   
   
   // Return HttpsURLConnection which trusts every certificate.
   public void open() throws java.lang.Exception
     {
	this.httpsUrlConn.connect();
     }
   
   public void setRequestProperty(String key, String value)
     {
	this.httpsUrlConn.setRequestProperty(key, value);
     }
   
   public String getHeaderField(String key)
     {
	return this.httpsUrlConn.getHeaderField(key);
     }
   
   public int getResponseCode() throws java.lang.Exception
    {
	// If we request responecode, write is over,
	// flush the bufferedwriter or the reciever wont get the data.
	this.flush();
	
	return this.httpsUrlConn.getResponseCode();
     }
      
   public String readLine() throws java.lang.Exception
     {
	int i;
	String result;
	
	// If we start reading, write is over.
	// flush the bufferedwriter or the reciever wont get the data.
	this.flush();
		
	if (this.BI == null)
	  {
	     this.BI = new BufferedInputStream( this.httpsUrlConn.getInputStream() );
	  }

	result = null;
	i = BI.read();
	if ( i != EOS )
	  {
	     result = "";
	     while (i != EOS && i != NEWLINE )
	       {
		  result = result + (char) i;
		  i = BI.read();
	       }
	  }
	
	return result;
     }
   
   public int read() throws java.lang.Exception
     {
	// If we start reading, write is over.
	// flush the bufferedwriter or the reciever wont get the data.
	this.flush();
		
	if (this.BI == null)
	  {
	     this.BI = new BufferedInputStream( this.httpsUrlConn.getInputStream() );
	  }
	return this.BI.read();
     }
   
   
   public int read(byte[] buffer, int offset, int length) throws java.lang.Exception
     {
	// If we start reading, write is over.
	// flush the bufferedwriter or the reciever wont get the data.
	this.flush();
		
	if (this.BI == null)
	  {
	     this.BI = new BufferedInputStream( this.httpsUrlConn.getInputStream() );
	  }
	return this.BI.read(buffer, offset, length);
     }
   
   
   public void write(String str) throws java.lang.Exception
     {
	byte[] buffer;
	
	if (this.BO == null)
	  {
	     this.BO = new BufferedOutputStream( this.httpsUrlConn.getOutputStream() );
	  }  
	buffer = str.getBytes();
	BO.write(buffer, 0, buffer.length); 
     }
   
   public void write(byte[] buffer, int offset, int length) throws java.lang.Exception
     {
	if (this.BO == null)
	  {
	     this.BO = new BufferedOutputStream( this.httpsUrlConn.getOutputStream() );
	  }
	this.BO.write(buffer, offset, length);
     }
		     
   public void close() throws java.lang.Exception
    {
       if ( this.BR != null )
	 {
	    BR.close();
	 }
       if ( this.BW != null )
	 {
	    BW.close();
	 }
       if ( this.BO != null )
	 {
	    BO.close();
	 }
              
       this.httpsUrlConn.disconnect();
    }
   

   public static void test(boolean disable_trustmanager)
     {
	HttpsConnection mhc;
	String readline;
	
	try 
	  {
	     mhc = new HttpsConnection("https://mig-1.imada.sdu.dk/cgi-sid/oneclick/envtest.py", disable_trustmanager);
	     mhc.open();
	     readline = mhc.readLine();
	     while( readline != null )
	       {
		  System.out.println(readline);
		  readline = mhc.readLine();
	       }
	     mhc.close();
	  }
	catch (java.lang.Exception e) 
	  {
	     e.printStackTrace();
	  }
     }
   
   public static void main(String[] argv)
     {
	HttpsConnection.test(false);
     }
}
