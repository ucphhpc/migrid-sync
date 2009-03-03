from timestamp import generate_name

def generate_mrsl(exec_commands, input_files, output_files, dest, executables=[], resource_specs_dict={}, runtime_env="", mem=100, disc=10, cpu_time=10, vgrid="Generic"):

    mrsl = []
    mrsl.append("::EXECUTE::\n")
    for cmd in exec_commands:
        mrsl.append(cmd+"\n")        
#    mrsl.append("tar -cf "+outputfile+" *.*\n")
	      #+ "--exclude vinter.license target.mvdml *.mvdscript compounds.mol2 \n")

    mrsl.append("\n::INPUTFILES::"+"\n")
    for path in input_files:
	mrsl.append(path+"\n")

    mrsl.append("\n::OUTPUTFILES::"+"\n")
    for f in output_files:
	mrsl.append(f+"\n")

    mrsl.append("\n::EXECUTABLES::"+"\n")
    for f in executables:
        mrsl.append(f+"\n")
    
    mrsl.append("\n::MEMORY::\n")
    mrsl.append(str(mem)+"\n")

    mrsl.append("\n::DISK::\n")
    mrsl.append(str(disc)+"\n")

    mrsl.append("\n::CPUTIME::\n")
    mrsl.append(str(cpu_time)+"\n")               
        


    for label, value in resource_specs_dict.iteritems():
        mrsl.append("\n::"+label+"::\n")
        mrsl.append(value+"\n")
        
    
    mrsl.append("\n::RUNTIMEENVIRONMENT::\n")                   
    mrsl.append(runtime_env+"\n")

    mrsl.append("\n::VGRID::\n")
    mrsl.append(vgrid+"\n")     

    mrsl_name = generate_name()
    mrsl_path = dest+mrsl_name
    mrsl_file = open(mrsl_path, "w")
    mrsl_file.writelines(mrsl)
    mrsl_file.close()
    return mrsl_path

