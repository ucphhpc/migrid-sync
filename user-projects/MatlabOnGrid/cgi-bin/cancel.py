#!/usr/bin/python 

import subprocess, os
import cgi
import cgitb
import time
import gridmatlab.configuration as config
from gridmatlab.miscfunctions import load_solver_data, update_solver_data
import miginterface as mig
import json
import cPickle
import traceback
import signal

cgitb.enable()

def main(form, output_format="json"):
  
    if form.has_key("name"):
        name = form["name"].value
    
    if form.has_key("output_format"):
        output_format = form["output_format"].value
    
    data_dict = load_solver_data(name)
    #jobs = data_dict["timesteps"][-1]["jobs"]
    output = ""
    try:
        os.kill(data_dict["pid"], signal.SIGTERM)
        output += "\n Grid solver process terminated."
    except OSError, err:
        if err.errno == 3:
            output += "\n Grid solver process is not running."
        else:
            output += "Error: "+str(err)
    for j in data_dict["timesteps"][-1]["jobs"]:    
        try:
    
            output += str(mig.cancel_job(j["job_id"]))
            #j["status"] = mig.job_status(j["job_id"])
    
        except Exception, e:
            output += "Error : "+str(e)
        #output += str(traceback.format_exc())
        
        #traceback.print_exc()
    
    #solver_data["timesteps"][-1]["status"] = "The server process has been cancelled."
    #data_dict["state"] = "Cancelled"
    try : 
        update_solver_data(name, status="The server process has been cancelled.", state="Cancelled")
    except Exception, e :
        output += str(e)
    
    
    if output_format == "json":
        output_dict = {"text" : output}
        #output_dict["text"] = output
        print "Content-type: application/json"
        print 
        print json.dumps((output_dict, 0))
    
    else:
        head = "<html><head></head>"
        text = "<body>%s</body>" % output
        text += "</html>"
        print "Content-type: text/html"
        print 
        print head
        print text
    
    #return "solver process started" 
main(cgi.FieldStorage())
    
    # submit
