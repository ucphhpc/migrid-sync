from rpy import r

def read_data(spss_data_file):
#file=fileimp, to.data.frame=TRUE)
    
    r("library('foreign')")
    data_sheet = r("read.spss(file='"+spss_data_file+"',to.data.frame=TRUE)")
    column_labels = data_sheet.keys()
    return column_labels
