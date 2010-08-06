main_script = "epistasis.py"
#data_file = "RfilesAndscripts/Inter99All290606.sav"
#data_file = "RfilesAndscripts/M101SNP210609W.sav"
#data_file = "RfilesAndscripts/M101comp120909W.sav"
data_file = "RfilesAndscripts/SkizoGWA1.sav"

main_r_file = "EpiMain.R"
r_files = ["EpiCRnew_R_edit.R","DistrPost07_R_edit.R","EpiLW.R"]

program_files = ["RfilesAndscripts/EpiMain.R", "RfilesAndscripts/EpiCRnew_R_edit.R","RfilesAndscripts/EpiLW.R","RfilesAndscripts/DistrPost07_R_edit.R", "RfilesAndscripts/epistasis.py"]

running_jobs_dir = "status_files"

monitor_polling_frequency = 20
gene_first_index = 5
gene_last_index = 600

trait_first_index = 3 #11 bt30
trait_last_index = 5#53 bt47 incl puls 46-47


default_job_size = 1

default_gene_list = range(gene_first_index,gene_last_index+1,1)#["rhnf4a2", "rhnf4a1", "rkir62"]
default_trait_list = range(trait_first_index,trait_last_index+1,1)#["Heigth","Alder","Omliv"] # height is misspelled purposely

default_selection_variable_index = 2
#default_selection_variable_label = "Gender"

default_variable_values = ["1","2"]#,"3","4","5","6","7","8","9","10","11","12","13","14"]#,"15"]
Epistasis_working_dir = "Epistasis_tmp/"

output_dir = "epifiles/"
# MiG specifications
resource_specs = {}
#resource_specs["ARCHITECTURE"] ="AMD64"
resource_specs["RUNTIMEENVIRONMENT"] = "GNU_R\nPYTHON-2"
resource_specs["VGRID"] = "DCSC"
resource_specs["CPUTIME"] = 120000
resource_specs["MEMORY"] = 2000
resource_specs["DISK"] = 1

#resource_specs["ARCHITECTURE"] = "AMD64"

default_user_output_dir = "epifiles/"

selection_variable_range = {'2':[1,2], '9':range(1,14)}

resultsdir_prefix_name = "EpistasisFiles"
tmp_local_job_dir = "EpiMigJobFiles"
main_results_dir = "epifiles/"

logfile_name = "logfile.txt"