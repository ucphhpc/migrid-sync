import sys, os, cPickle
sys.path.append('../Configuration/')
import Configuration.epistasisconfiguration as configuration

def create_init_job():
    """Return an initial epistasis job."""
    init_job = {}
    init_job["main_r_file"] = configuration.main_r_file
    init_job['r_files'] = configuration.r_files
    init_job['main_script'] = configuration.main_script
    init_job['output_dir'] = configuration.output_dir
    init_job["started"] = "---"
    init_job["finished"] = "---"
    init_job["status"] = "init"
    
    
    return init_job

def fragment_epistasis(job_size, values):
    """Return a list of sub jobs of size job_size."""
    value_range = []
    current_size = 0
    job_classes = []
    for i in range(len(values)):
        value_range.append(str(values[i]))
        current_size += 1
        if current_size == job_size:
            job_classes.append(value_range)
            value_range = []
            current_size = 0
    if value_range != []:
        job_classes.append(value_range)
    #print job_classes

    return job_classes




def gene_combinations(genes, size):
    combinations = []
    genes2 =  list(genes)
    genes2.reverse()
    for gene1 in genes:
        sublist = []
        for gene2 in genes2:
            
            if gene1 == gene2:
                sublist.reverse()
                combinations.extend(sublist)
                break
            entry = (gene1,gene2)
            sublist.append(entry)
    
    return combinations



def fragment_epistasis_1(classes, genes, traits, job_size):
    gene_tuples = gene_combinations(genes, 2)
    jobs = []
    #current_size = 0
    job = []
    for cl in classes: 
#        job["class"].append(cl) 
        for gp in gene_tuples:
            #for trait in traits:
    #            current_size += 1
            work_unit = (cl,gp,traits)
            job.append(work_unit)
            
            if len(job) == job_size:
                jobs.append(job)
                job = []
    if job != []:
        jobs.append(job)
    return jobs


def fragment_epistasis_alternate(classes, genes, traits, job_size):
    gene_tuples = gene_combinations(genes, 2)
    jobs = []
    #current_size = 0
    job = []
    #for cl in classes: 
#        job["class"].append(cl) 
    for gp in gene_tuples:
            #for trait in traits:
    #            current_size += 1
        work_unit = (classes,gp,traits)
        job.append(work_unit)
            
        if len(job) == job_size:
            jobs.append(job)
            job = []
    if job != []:
        jobs.append(job)

    return jobs


def get_job_specs(job):
    """Retrieve information aboutt the contents of a job""" 
    genes = set()
    #traits = set()
    classes = set()
    
    for j in job: 
        classes.add(str(j[0])) 
        for gene in j[1]:
            genes.add(gene)
     #   traits.set(j[2])
        
    return list(classes), list(genes), j[2]


# ##### CREATE JOBS#############

def create_epistasis_jobs(
    job_size,
    genelist,
    traitlist,
    selection_var,
    variable_values,
    data_file,
    output_dir,
    project_tag,
    run_local=False,
    ):
    """Return epistasis jobs that execute the epistasis procedure."""
    #values = configuration.selection_variable_range[str(selection_var)]
    #job_fragments = fragment_epistasis(classes=variable_values, genes=genelist, traits=traitlist, job_size=job_size)
    
    #partition the workload
    job_fragments = fragment_epistasis(job_size, values=variable_values)
    
    jobs = []
    ser_number = 1

    for j in job_fragments:
        # create basic job entities
        job = create_init_job()
        classes = j
        
        # global project name
        job['project_tag'] = project_tag
        job['class'] = classes
        job['gene_list'] = genelist
        job['trait_list'] = traitlist
        job['user_output_dir'] = output_dir
        # data set file
        job['data_file'] = os.path.basename(data_file)
        job['selection_variable'] = selection_var
        job['selection_var_values'] = variable_values
        # output file name
        output_filename = 'epifiles' + str(ser_number) + '.tar.gz'
        job_directory = configuration.tmp_local_job_dir\
             + str(ser_number) + '_' + project_tag + '/'
        # the jobs local pre execution working directory
        #job['job_dir'] = os.path.join(configuration.Epistasis_working_dir, job_directory)
        # output file for the job
        job['output_files'] = [output_filename]
        
        # directory to gather the results
        job_results_dir = configuration.resultsdir_prefix_name + project_tag +"/"
        job['results_dir'] = job_results_dir

        input_files = list(configuration.program_files)
        input_files.append(data_file)
        job['input_files'] = input_files
        job['resource_specs'] = configuration.resource_specs
        job['r_bin'] = '$R_HOME/bin/R'
        
        # write the job to a pickle file for storing input arguments and data needed on execution
        tmp_dir = "/tmp/"
        
        job_filename = "job_file%s.pkl"%ser_number
        
        job_filepath = os.path.join(tmp_dir,job_filename)
        output = open(job_filepath, 'w')
        cPickle.dump(job, output)
        job['input_files'].append(job_filepath)
        output.close()

        # the execution command on the grid resource
        job_cmds = ['$PYTHON '+ job['main_script'] + ' '+job_filename]

        # mig settings
        job['commands'] = job_cmds
        
        jobs.append(job)
        ser_number += 1

    return jobs, job_results_dir



if __name__ == '__main__':

    traits = ["t1","t2", "t3", "t4", "t5"]
    genes = ["g1","g2", "g3", "g4", "g5", "g6"]
    classes = range(2)


    traits = ["t1","t2"]
    genes = ["g1","g2", "g3"]
    classes = range(2)

    jobs = fragment_epistasis_alternate(classes, genes, traits, 2)
    print jobs 


    #print get_job_specs(jobs[0])
