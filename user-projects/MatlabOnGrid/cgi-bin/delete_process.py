#!/usr/bin/python 

import subprocess, os
import cgi
import cgitb
import time
import gridmatlab.configuration as config
import miginterface as mig
import json
import cPickle
import traceback
import signal
import shutil

cgitb.enable()

def main(form, output_format="json"):
    output = ""
    if form.has_key("name"):
        name = form["name"].value
    
    if form.has_key("output_format"):
        output_format = form["output_format"].value
    
    grid_proc_file = config.grid_application_exec
    
    job_data_dir = os.path.join(config.jobdata_directory, name)
    solver_data_path = os.path.join(job_data_dir, config.solver_data_file)
    data_file = open(solver_data_path)
    data_dict = cPickle.load(data_file)
    #jobs = data_dict["timesteps"][-1]["jobs"]
    if data_dict.has_key("state") and data_dict["state"] == "Running":
        output += "The server process is running. Please cancel before deleting."
    else:
    
    
        try:
            shutil.rmtree(job_data_dir)
            
            
            output += "\n Process deleted."
        except OSError, err:
            output += "Error: "+str(err)
        
   
    if output_format == "json":
        output_dict = {"text" : output}
        #output_dict["text"] = output
        print "Content-type: application/json"
        print 
        print json.dumps((output_dict, 0))
    
    else:
        head = "<html><head></head>"
        text = "<body><div id='mycontent'>%s</div></body>" % output
        text += "</html>"
        print "Content-type: text/html"
        print 
        print head
        print text
    
    #return "solver process started" 
main(cgi.FieldStorage())
    
    # submit
