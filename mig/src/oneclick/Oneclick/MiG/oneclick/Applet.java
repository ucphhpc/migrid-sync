/*
# Applet - OneClick resource applet
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
  
import java.awt.*;
import java.net.URL;

public class Applet extends java.applet.Applet
{
   private int jobs_done;
   private int jobs_failed;
   private String resource_name;
   private String server;
   private String status_msg;
   private Image execute_image;
        
   private Resource resource;
   private Thread resource_thread;
       
   /* This method is called when applet starts */
   public void init()
     {
	this.jobs_done = 0;
	this.jobs_failed = 0;
	this.resource_name = "";
	this.server = "";
	this.status_msg = "";
	this.execute_image = null;

	System.out.println("server: " + this.getParameter("server"));
	System.out.println("sandboxkey: " + this.getParameter("sandboxkey"));
	System.out.println("resource_name: " + this.getParameter("resource_name"));
	System.out.println("cputime: " + this.getParameter("cputime"));
		
	try
	  {
	     //this.exe = new Exe(thisthis.getParameter("server"), this.getParameter("sandboxkey"), this.getParameter("resource_name"));
	     this.resource = new Resource(this);
	       
	       //this.getParameter("server"), this.getParameter("sandboxkey"), this.getParameter("resource_name"));
	     resource_thread = new Thread(this.resource);
	     resource_thread.start();
	  }
	catch (java.lang.Exception e){e.printStackTrace();}
	     	
     } // end init

   // update is invoked by repaint.
   // Instead of calling the 'java.applet.Applet' update function
   // vi override it and call paint
   public void update(Graphics g)
     {
	this.paint(g);
     } // end of update

   // Overrides the 'java.applet.Applet' repaint function
   public void repaint()
     {
	this.jobs_done = this.resource.getJobsDone();
	this.jobs_failed = this.resource.getJobsFailed();
	this.resource_name = this.resource.getResourceName();
	this.server = this.resource.getServer();
	this.status_msg = this.resource.getStatusMsg();
	
	// New image is retrieved just before executing
	if ( this.resource.getStatus() == this.resource.EXECUTING_JOB )
	  {
	     this.execute_image = this.resource.getExecuteImage();
	  }
	
	// Invoke 'java.applet.Applet.repaint()'
	super.repaint();
     } // end of repaint
   
   
   public void paint(Graphics g)
    {
       Image buffer_image;
       Graphics buffer_g;

       this.setBackground(Color.black);

       buffer_image = this.createImage(this.size().width, this.size().height);
       buffer_g = buffer_image.getGraphics();
       buffer_g.setFont(new Font("Arial",Font.BOLD,18)); //set the font
       buffer_g.setColor(Color.white); //set the color
       
       if (this.execute_image != null )
	 {
	     buffer_g.drawImage(this.execute_image, 0, 0, this);
	  }
       
       buffer_g.drawString("MiG Resource: " + this.resource_name,15,30); //draw the message
       buffer_g.drawString("MiG Server: " + this.server,15,55); //draw the message
       
       buffer_g.drawString("MiG Status: " + this.status_msg,15,80); //draw the message
       buffer_g.drawString("MiG Jobs done: " + this.jobs_done,15,105); //draw the message
       buffer_g.drawString("MiG Jobs failed: " + this.jobs_failed, 15,130); //draw the message
       

       g.drawImage(buffer_image, 0, 0, this);

    } //end of paint method
   
   /* This method gets called when the applet is terminated--
    * when the user goes to another page or exits the browser.
    */
   public void stop ( ) {
      System.out.println("stop");
      if ( this.resource_thread.isAlive() )
	this.resource_thread.stop();
      // no actions needed in this Applet
   } // end stop
   
   /* method destroy
    * desription: to destroy the applet
    */
   public void destroy ( ) {
      System.out.println("DESTROY");
      if ( this.resource_thread.isAlive() )
	this.resource_thread.destroy();
      //no actions needed in this Applet
   } // end destroy
} // end of HelloWorld
 
