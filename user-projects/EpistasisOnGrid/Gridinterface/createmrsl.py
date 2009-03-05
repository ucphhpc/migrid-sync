from timestamp import generate_name

def generate_mrsl(exec_commands, input_files, output_files, dest, executables=[], resource_specs_dict={}, mem=10, disc=10, cpu_time=10):
    """Generate an mRSL file to submit a MiG job. Returns a string path to the file."""

    mrsl = []
    mrsl.append("::EXECUTE::\n")
    for cmd in exec_commands:
        mrsl.append(cmd+"\n")        

    mrsl.append("\n::INPUTFILES::"+"\n")
    for path in input_files:
	mrsl.append(path+"\n")

    mrsl.append("\n::OUTPUTFILES::"+"\n")
    for f in output_files:
	mrsl.append(f+"\n")

    mrsl.append("\n::EXECUTABLES::"+"\n")
    for f in executables:
        mrsl.append(f+"\n")

    for label, value in resource_specs_dict.iteritems():
        mrsl.append("\n::"+label+"::\n")
        mrsl.append(str(value)+"\n")

    if not resource_specs_dict.has_key("MEMORY"):
        mrsl.append("\n::MEMORY::\n")
        mrsl.append(str(mem)+"\n")

    if not resource_specs_dict.has_key("DISK"):
        mrsl.append("\n::DISK::\n")
        mrsl.append(str(disc)+"\n")
            
    if not resource_specs_dict.has_key("CPUTIME"):
        mrsl.append("\n::CPUTIME::\n")
        mrsl.append(str(cpu_time)+"\n")               
            
    mrsl_name = generate_name()
    mrsl_path = dest+mrsl_name
    mrsl_file = open(mrsl_path, "w")
    mrsl_file.writelines(mrsl)
    mrsl_file.close()
    return mrsl_path

"""    
mrsl.append("\n::RUNTIMEENVIRONMENT::\n")                   
mrsl.append(runtime_env+"\n")

mrsl.append("\n::VGRID::\n")
mrsl.append(vgrid+"\n")     
"""
