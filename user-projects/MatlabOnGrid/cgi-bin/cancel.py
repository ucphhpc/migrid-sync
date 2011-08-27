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

cgitb.enable()

def main(form, output_format="json"):
  
    if form.has_key("name"):
        name = form["name"].value
    
    if form.has_key("output_format"):
        output_format = form["output_format"].value
    
    grid_proc_file = config.grid_application_exec
    
    job_data_dir = os.path.join(config.jobdata_directory, name)
    solver_data_path = os.path.join(job_data_dir, config.solver_data_file)
    data_file = open(solver_data_path)
    data_dict = cPickle.load(data_file)
    jobs = data_dict["timesteps"][-1]["jobs"]
    output = ""
    try:
        os.kill(data_dict["pid"], signal.SIGTERM)
        output += "\n Grid solver process terminated."
    except OSError, err:
        if err.errno == 3:
            output += "\n Grid solver process is not running."
        else:
            output += "Error: "+str(err)
        
    try:
        for j in jobs:
            output += mig.cancel_job(j["job_id"])
    
    except Exception, e:
        output += "Error : "+str(e)
        output += str(traceback.format_exc())
        
        traceback.print_exc()
    
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
