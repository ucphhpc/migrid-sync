#!/usr/bin/python

import os
import subprocess
import cPickle
import cgi
import cgitb
import gridmatlab.configuration as config
from gridmatlab.miscfunctions import get_process_data
cgitb.enable()

scripts = """<link rel="stylesheet" type="text/css" href="http://dk.migrid.org/images/site.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="/images/css/matlab_on_grid.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="http://dk.migrid.org/images/default.css" media="screen"/>
<link rel="stylesheet" type="text/css" href="http://dk.migrid.org/images/css/jquery.managers.css" media="screen"/>

<script type="text/javascript" src="http://code.jquery.com/jquery-1.6.1.min.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui-1.8.16.custom.min.js"></script>
<script type="text/javascript" src="/images/js/matlab.js"></script>

<script type="text/javascript">
window.onload= function(){ 
setTimeout("window.location.reload()", 10000);
};


$(document).ready( function() {
    
  });

</script>  
""" 

def main(form):
    html = ""

    if form.has_key("solver_name"):
        global solver_name
        solver_name = form["solver_name"].value
        data = get_process_data(solver_name)
       
        html = create_overview(data)
    else:
        html = create_view()
        
    head = "<html><head>%s</head>" % scripts
    text = "<body><div id='content' >%s</div></body></html>" % html
    print "Content-type: text/html"
    print 
    print head
    print text


def create_view():
    html = "<h1>Process monitor</h1>"
    solvers = os.listdir(config.jobdata_directory)
    solvers.sort()
    for name in solvers:
        html += "<a href='/cgi-bin/monitor.py?solver_name=%s'>%s</a> <br>" % (name, name)
    return html


def create_overview(data_dict):
    html = "<h1>Monitor for %s </h1>"% solver_name
    timesteps = data_dict["timesteps"]
    for t in timesteps: # descending
        html += create_timestep_overview(t)+"<hr>"
        
    html += "<button class='cancel' solvername=%s type='button'>Stop</button>" % solver_name
    html += "<a href='%s'> Go to files </a>"% (os.path.join(config.job_files_url, solver_name))
    
    return html

def create_timestep_overview(timestep_dict):
    
    html = "<div><ul>"
     
    for k in timestep_dict.keys():
        if not k in ["jobs", "utility_file"]:
            html += "<li>%s: %s</li>" % (k, timestep_dict[k])
    
    if timestep_dict.has_key("utility_file"):
        util_path = os.path.join(config.job_files_url, solver_name, timestep_dict["utility_file"])
        html += "<li>%s : <a href='%s'> %s</a> </li>" % ("utility_file", util_path, timestep_dict["utility_file"])
        
    html += "<li>%s</li>" % create_jobs_table(timestep_dict["jobs"])
    
    html += "</ul></div>"
    return html

def create_jobs_table(jobs):
    table = "<table id='jm_jobmanager'>"
    if jobs: # make a header 
        table += "<thead><tr>"
        columns = ["job_id", "status", "worker_index"]
        
        for k in columns:
             table += "<th>%s</th>" % k
        table += "</thead></tr>"
    
    table += "<tbody>"
    for j in jobs:
        table += "<tr>"
        for c in columns:
           table += "<td>%s</td>" % j[c]
        table += "</tr>"
    table += "</tbody>"
    table += "</table>"
    
    
    return table


solver_name = ""
job_data_dir = ""
main(cgi.FieldStorage())

