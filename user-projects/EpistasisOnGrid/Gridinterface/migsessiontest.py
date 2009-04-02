
import migsession
import timestamp

timestamp = timestamp.generate_timestamp()
test_working_dir = "testworkdir/" 
test_job_dir = "testjobdir"+timestamp+"/"
test_result_dir = test_job_dir
#os.mkdir(test_dir)
input_file = "test.txt"
output_file = "testout.txt"

text = "mig test"
test_file = open(input_file, "w")
test_file.write("mig test")
test_file.close()

cmd = "cat "+input_file+" > "+output_file
input_files = [input_file]

output_files = [output_file]
output_dir = test_result_dir

job = {}
job["input_files"] = input_files
job["output_files"] = output_files
job["commands"]  = [cmd]
job["job_dir"] = test_job_dir
job["results_dir"] = test_job_dir
job["resource_specs"] = {}
log = "logfile.txt"
session = migsession.MigSession(test_result_dir, log)

session.create_mig_job(job)
session.wait_for_jobs([job])
files = session.handle_output(job)

succes = files[0].split("/")[-1] == job["output_files"][0]
succes = succes and open(files[0],"r").readlines() == open(job["results_dir"]+job["output_files"][0],"r").readlines()
if succes:
    print "MiG test successful"
    session.clean_up([job])
else:
    print "MiG test failed."


