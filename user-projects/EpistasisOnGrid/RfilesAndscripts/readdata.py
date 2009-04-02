#from rpy_options import set_options
#set_options(RHOME='/usr/local/lib64/R-2.8.0')
#from rpy import *

from rpy import r

def read_data(spss_data_file):
    r("library('foreign')")

    r("data = read.spss(file='"+spss_data_file+"',to.data.frame=TRUE)")
    data_sheet = r("data")
    num_columns = len(data_sheet.keys())
    
    column_labels = []
    data_list = []
    for i in range(1,num_columns+1):
        #column_label = 
        column = r("data["+str(i)+"]")
        label = column.keys()[0] # only has one key 
        column_labels.append(label) 
        data_list.append(column[label])

    return data_list, column_labels

def read_data_old(spss_data_file):
#file=fileimp, to.data.frame=TRUE)
    
    r("library('foreign')")
    #r("library('stats')")
    data_sheet = r("read.spss(file='"+spss_data_file+"',to.data.frame=TRUE)")
    #print data_sheet
    #exit(0)
    #column_labels = data_sheet.keys()
    
    #exit(0)
#for label, values in data_sheet.items():
    #    new_vals = map(lambda x:if not is.str(x) : str(x), values)
     #   data_sheet[label] = new_vals
    
    return data_sheet #column_labels



def get_by_index(spss_data_file, gene_index_1, gene_index_2, trait_index_1, trait_index_2):
    r("data = read.spss(file='"+spss_data_file+"',to.data.frame=TRUE)")
    gene_index = str(gene_index_1)+":"+ str(gene_index_2)
    genes = r("names(data["+gene_index+"])")
    trait_index = str(trait_index_1)+":"+ str(trait_index_2)
    traits = r("names(data["+trait_index+"])")
    #print genes
    #print traits

    return genes, traits
