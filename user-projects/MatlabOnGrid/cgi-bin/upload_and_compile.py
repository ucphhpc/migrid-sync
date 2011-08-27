#!/usr/bin/python

"""Upload and compile a matlab file"""

import os
import subprocess
import gridmatlab.configuration as config
from gridmatlab.miscfunctions import upload_file, log
import cgi
import cgitb


cgitb.enable()


def main(form):

    file_item = None
    file_name = 'nofile'

    if form.has_key('file') and form['file'] != "" :
        file_item = form['file']
        file_name = file_item.filename
        
        file_location = config.upload_directory
        path = os.path.join(file_location, file_name)
        returncode, msg = upload_file(file_item, path)
    
        if returncode == 0:
            msg = compile_file(path, config.matlab_binary)
            clean_dir(config.upload_directory)

    else:
        msg = "No file found."
        
    head = "<html><head></head>"
    text = "<body>%s</body></html>" % msg
    print "Content-type: text/html"
    print 
    print head
    print text


def clean_dir(path):
    files = os.listdir(path)
    for f in files:
        file_path = os.path.join(path, f)
        if os.path.exists(file_path):
            os.remove(file_path)


def compile_file(path, output_path):
    
    compile_cmd = "mcc -m %s -d %s -o %s" % (path, os.path.dirname(output_path), os.path.basename(output_path))
   
    proc = subprocess.Popen(compile_cmd, cwd=config.compile_directory, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    out, err = proc.communicate()
    log(out)
    if err: 
        log("Error message: "+err)
    output = " ".join([out,err, str(proc.returncode)])
    
    return output
    

main(cgi.FieldStorage())
