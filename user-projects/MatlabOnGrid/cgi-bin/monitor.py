#!/usr/bin/python

import os
import subprocess
import cPickle
import cgi
import cgitb
import gridmatlab.configuration as config
from gridmatlab.miscfunctions import load_solver_data
cgitb.enable()

scripts = """<link rel="stylesheet" type="text/css" href="http://dk.migrid.org/images/site.css" media="screen"/>

<link rel="stylesheet" type="text/css" href="http://dk.migrid.org/images/default.css" media="screen"/>
<!--<link rel="stylesheet" type="text/css" href="http://dk.migrid.org/images/css/jquery.managers.css" media="screen"/>-->
<link rel="stylesheet" type="text/css" href="/images/css/matlab_on_grid.css" media="screen"/>


<script type="text/javascript" src="http://code.jquery.com/jquery-1.6.1.min.js"></script>
<script type="text/javascript" src="/images/js/jquery-ui-1.8.16.custom.min.js"></script>
<script type="text/javascript" src="/images/js/matlab.js"></script>

<script type="text/javascript">
window.onload= function(){ 
setTimeout("window.location.reload()", 30000);
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
        data = None
        
        if os.path.exists(os.path.join(config.jobdata_directory, solver_name, config.solver_data_file)):
            data = load_solver_data(solver_name)
            html = create_process_view(data)
        else:
            html = "No process data found."
    else:
        html = create_process_list()
        
    head = "<html><head>%s</head>" % scripts
    text = "<body><div id='mycontent' >%s</div></body></html>" % html
    print "Content-type: text/html"
    print 
    print head
    print text


def sort_by_date(files):
    file_time = []
    for f in files: 
        file_time.append((os.stat(os.path.join(config.jobdata_directory ,f)).st_mtime, f))
    file_time.sort()
    sorted_files = [ft[1] for ft in file_time]
    return sorted_files
    
def create_process_list():
    
    solver_dirs = os.listdir(config.jobdata_directory)
    solver_dirs.remove(".svn")
    solvers = sort_by_date(solver_dirs)
    
    proc_table = "<table class='proc_table'><th>Name</th><th></th>"
    for name in solvers:
        #proc_table += "<tr><td><a href='/cgi-bin/monitor.py?solver_name=%s'>%s</a></td> <td><button id='delete_process' filename='%s' > Delete</button></td></tr>" % (name, name, name)
        proc_table += "<tr><td><a href='/cgi-bin/monitor.py?solver_name=%s'>%s</a></td> <td><img id='delete_process' src='/images/icons/Delete-icon.png' width='8' filename='%s'/> </td></tr>" % (name, name, name)
    proc_table += "</table>"
    html = "<h1>Process monitor</h1>"+proc_table
    return html


def create_process_view(data_dict):
    html = "<h1>Monitor for %s </h1>"% solver_name
    
    status_summary = "<div class='status_summary'><ul >"
    
    for k, v in data_dict.items():
        if k == "timesteps":
            status_summary += "<li>timesteps completed: %s</li>" % (len(v)-1)
        else:    
            status_summary += "<li>%s: %s</li>" % (k, v)
    
    status_summary += "</ul>"
    html += status_summary
    html += "<br><br>"
    
    
    
    html += "<button class='cancel' solvername=%s type='button'>Cancel</button>" % solver_name
    html += "<a href='%s'> Go to files </a>"% (os.path.join(config.job_files_url, solver_name))
    html += "</div>"
  
    
    html += "<h2>Timestep list</h2>"
    timesteps = data_dict["timesteps"]
    timesteps.reverse()
    for t in timesteps: # ascending
        html += create_timestep_overview(t)+"<hr>"
        

    
    return html

def create_timestep_overview(timestep_dict):
    
   
    html = "<div><ul>"
    for k in timestep_dict.keys():
        if not k in ["jobs"]:
            html += "<li>%s: %s</li>" % (k, timestep_dict[k])
        
    html += "<li>%s</li>" % create_jobs_table(timestep_dict["jobs"])
    
    html += "</ul></div>"
    return html

def create_jobs_table(jobs):
    table = "<table id='jm_jobmanager'>"
    if jobs: # make a header 
        table += "<thead><tr>"
        columns = ["job_id", "status", "worker_index", "executing", "finished"]
        
        for k in columns:
             table += "<th>%s</th>" % k
        table += "</thead></tr>"
    
    table += "<tbody>"
    for j in jobs:
        table += "<tr>"
        for c in columns:
            if j.has_key(c):
                table += "<td>%s</td>" % j[c]
            else:
                table += "<td>NA</td>"
        table += "</tr>"
    table += "</tbody>"
    table += "</table>"
    
    
    return table


solver_name = ""
job_data_dir = ""
main(cgi.FieldStorage())

