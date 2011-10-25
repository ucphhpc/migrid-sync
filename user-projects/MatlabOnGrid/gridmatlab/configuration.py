import os
import user_settings

# DIRECTORIES
root_directory = user_settings.root_directory
file_directory = os.path.join(root_directory, "files")
jobdata_directory = os.path.join(file_directory, "job_data")
upload_directory = os.path.join(file_directory, "upload")
compile_directory = os.path.join(file_directory, "compiled")
logs_directory = os.path.join(root_directory, "logs")

working_dir = "gridmatlab"
results_dir_name = "old_result_files_dir"

# WEB URLS
job_files_url = "/jobdata/"

# FILES
matlab_executable = os.path.join(compile_directory, "run_solve_problem_for_one_index_set.sh")
matlab_binary = os.path.join(compile_directory, "solve_problem_for_one_index_set")
grid_application_exec = "grid_solver.py"  
log_file = os.path.join(logs_directory, "main_log.txt")
server_proc_output = os.path.join(logs_directory, "server_proc_output.txt")
postprocessing_code = os.path.join(root_directory, working_dir, "summarize_data_after_time_t.m")
solver_data_file = "solver_data.pkl"
MCR_path = user_settings.MCR_path

#  MIG
mig_specifications = {"VGRID":"DIKU", "RUNTIMEENVIRONMENT":"MATLAB_MCR", "MEMORY":"2000"}
matlab_rte = "$MATLAB_MCR"


# SOLVER SETTINGS
INIT_TIMESTEP = 81
FINAL_TIMESTEP = 1
POLLING_INTERVAL = 10 # seconds
