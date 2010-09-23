"""
Tools for generating an mRSL file.
"""

import os

def generate_mrsl(mrsl_file_path, exec_commands, input_files, output_files, mig_output_target_directory="", executables=[], resource_specifics={}):
    """Generate an mRSL file to submit a MiG job. Returns a string path to the file."""

    mrsl = []
    mrsl.append("::EXECUTE::\n")
    if isinstance(exec_commands, list):
        for cmd in exec_commands:
            mrsl.append(cmd+";\n")
    else:
        mrsl.append(exec_commands+";\n")

    mrsl.append("\n::INPUTFILES::"+"\n")
    for path in input_files:
        filename = os.path.basename(path)
        mrsl.append(path+" "+filename+"\n")

    mrsl.append("\n::OUTPUTFILES::"+"\n")
    for path in output_files:
        filename = os.path.basename(path)
        mig_path = filename
        if mig_output_target_directory != "":
            mig_path = os.path.join(mig_output_target_directory, filename)
        mrsl.append(path+" "+mig_path+"\n")

    mrsl.append("\n::EXECUTABLES::"+"\n")
    for f in executables:
        mrsl.append(f+"\n")

    for label, value in resource_specifics.iteritems():
        mrsl.append("\n::"+label+"::\n")
        mrsl.append(str(value)+"\n")

    mrsl_file = open(mrsl_file_path, "w")
    mrsl_file.writelines(mrsl)
    mrsl_file.close()
