"""
Tools for generating an mRSL file.
"""

import os

def generate_mrsl(mrsl_file_path, exec_commands, input_files="", output_files="", mig_output_target_directory="", executables="", resource_specifics={}):
    """Generate an mRSL file to submit a MiG job. Returns a string path to the file."""

    mrsl = []
    mrsl.append("::EXECUTE::\n")
    if isinstance(exec_commands, list):
        for cmd in exec_commands:
            mrsl.append(cmd+"\n")
    else:
        mrsl.append(exec_commands+"\n")
    
    if input_files != "":
        mrsl.append("\n::INPUTFILES::"+"\n")
        if isinstance(input_files, list):
            for path in input_files:
                #filename = os.path.basename(path)
                #mrsl.append(filename+" "+filename+"\n")
                mrsl.append(path+"\n")
        else:
            mrsl.append(input_files+"\n")
        
    if output_files != "":
        mrsl.append("\n::OUTPUTFILES::"+"\n")
        if isinstance(output_files, list):
            for path in output_files:
                #filename = os.path.basename(path) 
                #mig_path = filename # transfer the file to the root in users mig home
                #if mig_output_target_directory != "":
                #    mig_path = os.path.join(mig_output_target_directory, filename)
                #mrsl.append(path+" "+mig_path+"\n") 
                mrsl.append(path+"\n")
                # issue is whether to limit the user to always using the root dir.
    if executables != "":
        mrsl.append("\n::EXECUTABLES::"+"\n")
        if isinstance(executables, list):
            for path in executables:
                #filename = os.path.basename(path)
                #mrsl.append(filename+" "+filename+"\n")
                mrsl.append(path+"\n")
        else:
            mrsl.append(input_files+"\n")
    
    
    for label, value in resource_specifics.iteritems():
        mrsl.append("\n::"+label+"::\n")
        if isinstance(value, list):
            for val in value:
                mrsl.append(str(val)+"\n")
        else:
            mrsl.append(str(value)+"\n")

    mrsl_file = open(mrsl_file_path, "w")
    mrsl_file.writelines(mrsl)
    mrsl_file.close()
