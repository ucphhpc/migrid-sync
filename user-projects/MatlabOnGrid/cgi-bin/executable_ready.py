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
  
    #if form.has_key("filename"):
    #    name = form["filename"].value
    
    if form.has_key("output_format"):
        output_format = form["output_format"].value
    
    
    files_exist = os.path.exists(config.matlab_executable) and os.path.exists(config.matlab_binary)
    output = str(int(files_exist)) 
    
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
