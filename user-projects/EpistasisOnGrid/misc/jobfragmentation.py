

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
