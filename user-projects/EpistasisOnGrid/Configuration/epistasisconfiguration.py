main_script = "epistasis.py"
data_file = "RfilesAndscripts/Inter99All290606.sav"

r_files = ["EpiCRnew_R_edit.R","DistrPost07_R_edit.R", "EpiPS_R_edit.R", "HWEwigNew_R_edit.R"]

program_files = ["RfilesAndscripts/EpiMain.R", "RfilesAndscripts/EpiCRnew_R_edit.R","RfilesAndscripts/DistrPost07_R_edit.R", "RfilesAndscripts/EpiPS_R_edit.R", "RfilesAndscripts/HWEwigNew_R_edit.R", "RfilesAndscripts/epistasis.py"]

monitor_polling_frequency = 5
gene_first_index = 74 #74
gene_last_index = 75 #103

trait_first_index = 7 #7 
trait_last_index = 8 #37 
selection_variable_index = 2
default_variable_values = [1,2]
Epistasis_working_dir = "Epistasis_tmp/"

output_dir = "epifiles/"
# MiG specifications
resource_specs = {}
#resource_specs["ARCHITECTURE"] ="AMD64"
resource_specs["RUNTIMEENVIRONMENT"] = "GNU_R"
resource_specs["VGRID"] = "DCSC"
resource_specs["CPUTIME"] = 120
resource_specs["MEMORY"] = 100
resource_specs["DISK"] = 10

default_user_output_dir = "epifiles/"

selection_variable_range = {'2':[1,2], '5':range(1,20)}

resultsdir_prefix_name = "EpistasisFiles"
tmp_local_job_dir = "EpiMigJobFiles"
main_results_dir = "epifiles/"
