import os

# DIRECTORIES

root_directory = #PATH TO MATLAB ROOT
file_directory = os.path.join(root_directory, "matlab_files")
jobdata_directory = os.path.join(file_directory, "job_data")
upload_directory = os.path.join(file_directory, "upload")
compile_directory = os.path.join(file_directory, "compiled")

working_dir = "gridmatlab"


# WEB URLS

job_files_url = "/jobdata/"

# FILES

matlab_executable = os.path.join(compile_directory, "run_solve_problem_for_one_index_set.sh")
matlab_binary = os.path.join(compile_directory, "solve_problem_for_one_index_set")
grid_application_exec = "grid_solver.py"  
log_file = os.path.join(root_directory, "log.txt")
postprocessing_code = os.path.join(root_directory, working_dir, "summarize_data_after_time_t.m")
solver_data_file = "solver_data.pkl"
MCR_path = # PATH TO Matlab Runtime Environment

#  MIG

matlab_rte = "$MATLAB_MCR"

# SOLVER SETTINGS

INIT_TIMESTEP = 81
