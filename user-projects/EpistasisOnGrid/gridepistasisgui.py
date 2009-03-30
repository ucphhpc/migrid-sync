import sys
sys.path.append("GUI/")
import  epistasisviewer as viewer
import gridepistasis as EpiModel
import wx
import time
import os
sys.path.append("RfilesAndscripts/")
import readdata

exec_state = "executing"
pending_state = "pending"
finished_state = "finished"
cancelled_state = "cancelled"

gene_selection = set()
gene_selection_dict = {}
trait_selection = set()
trait_selection_dict = {}
class_selection = list()
all_genes_and_traits = list()
data_sheet = []

def popup_box(comment, caption_title=" "):
    dlg = wx.MessageDialog(frame_1,
                           message=comment,
                           caption=caption_title,
                           style=wx.OK|wx.ICON_INFORMATION
                           )
    dlg.ShowModal()
    dlg.Destroy()

############################
######## GENE SELECTOR TAB###########
#############################
def read_data_sheet():
    datafile = frame_1.datafile.GetValue()
    if not os.path.exists(datafile):
        popup_box("Can't find "+datafile)
        return
    #print all_genes_and_traits
    #data_sheet.update(readdata.read_data(datafile))
    data_list, column_labels = readdata.read_data(datafile)
    data_sheet.extend(data_list)
    #column_labels = data_sheet.keys()
    all_genes_and_traits.extend(column_labels)
    #print "all", all_genes_and_traits
    #all_genes_and_traits.sort()
    frame_1.gene_list.Set(all_genes_and_traits)
    frame_1.trait_list.Set(all_genes_and_traits)
    frame_1.selection_variable_list.SetItems(all_genes_and_traits)

##### BUTTONS ############                        

def update_selected_genes():
    frame_1.selected_genes.Set(list(gene_selection))

def on_add_genes(event=None):
    indexes = frame_1.gene_list.GetSelections()
    #indexes = list(index)
    #print indexes, all_genes_and_traits
    #frame_1.selected_genes.InsertItems(index, 0)
    for i in indexes: 
#        gene_name = all_genes_and_traits[i]
        #if not gene_name in gene_selection:
        #gene_selection.append(all_genes_and_traits[i])
        gene_name = all_genes_and_traits[i]
        gene_selection.add(gene_name)
        if not gene_selection_dict.has_key(gene_name):
            gene_selection_dict[gene_name] = i
    update_selected_genes()
    
def on_remove_genes(event=None):
    indexes = list(frame_1.selected_genes.GetSelections())
    indexes.reverse()
    #print indexes
    
    for i in indexes: 
        gene_name = list(gene_selection)[i] # list converts from set to list
        gene_selection.remove(gene_name)
        del(gene_selection_dict[gene_name])
    #gene_selection.remove(genes)
    update_selected_genes()
 
###########################
######## TRAIT SELECTOR TAB###########
##########################


##### BUTTONS ############                        

def update_selected_traits():
    frame_1.selected_traits.Set(list(trait_selection))

def on_add_traits(event=None):
    indexes = frame_1.trait_list.GetSelections()
    #indexes = list(index)
    print indexes, all_genes_and_traits
    #frame_1.selected_genes.InsertItems(index, 0)
    for i in indexes: 
        trait_name = all_genes_and_traits[i]
        #if not gene_name in gene_selection:
        #gene_selection.append(all_genes_and_traits[i])
        trait_selection.add(trait_name)
        if not trait_selection_dict.has_key(trait_name):
            trait_selection_dict[trait_name] = i
            
    update_selected_traits()
    
def on_remove_traits(event=None):
    indexes = list(frame_1.selected_traits.GetSelections())
    indexes.reverse()
    print indexes
    
    for i in indexes: 
        trait_name = list(trait_selection)[i] # list converts set 
        trait_selection.remove(trait_name)
        del(trait_selection_dict[trait_name])
    #gene_selection.remove(genes)
    update_selected_traits()

##########################
#### GENERAL TAB ############
#########################

def validateInput():
    try: 
        g1 = int(frame_1.g1.GetValue())
        g2 = int(frame_1.g2.GetValue())
        t1 = int(frame_1.t1.GetValue())
        t2 = int(frame_1.t2.GetValue())
#        sv = int(frame_1.sv.GetValue())
        #c1 = int(frame_1.c1.GetValue())
        #c2 = int(frame_1.c2.GetValue()) 
    except ValueError:
        return False, "Index values must be integers"
#if type(g1) != type(1) and type(g2) != type(1):
#     return False, "Genes indexes must be integers"

#if type(t1) != type(1) and type(t2) != type(1):
#   return False, "Trait indexes must be integers"
     
#if type(sv) != type(1) :
# return False, "Selection variable index must be an integer"
    datafile = frame_1.datafile.GetValue()
    outputdir = frame_1.outputdir.GetValue()   
 #type(sv) != type(1)
    if not os.path.exists(datafile):
        return False, "Can't find data file : "+datafile
    
    if not os.path.exists(outputdir):
        return False, "Can't find output directory : "+outputdir
   
    return True, "OK"
    
##### START/ STOP #############

def start():
    valid, comment = validateInput()
    if not valid: 
        popup_box(comment, "Incorret input")
        return


    #collect values
    datafile = frame_1.datafile.GetValue()
    outputdir = frame_1.outputdir.GetValue()
    local_mode = frame_1.runlocal.GetValue()
    #selected_genes = list(frame_1.selected_genes.GetSelections())
    
    if outputdir[-1] != "/":
        outputdir += "/"



    if frame_1.use_indexes.GetValue():
        g1 = int(frame_1.g1.GetValue())
        g2 = int(frame_1.g2.GetValue())
        t1 = int(frame_1.t1.GetValue())
        t2 = int(frame_1.t2.GetValue())
        #sv = frame_1.sv.GetValue()
        #c1 = frame_1.c1.GetValue()
        #c2 = frame_1.c2.GetValue()
        genes = range(g1,g2+1)
        traits = range(t1,t2+1)
        #, traits = readdata.get_by_index(datafile,g1,g2,t1,t2)
        
    else:
        genes = gene_selection_dict.values()
        traits = trait_selection_dict.values()

    list_pos = frame_1.selection_variable_list.GetSelection()+1 # indexes start at 1 in R
    #print sel_var
    selection_variable = list_pos
    #select_variable_values = data_sheet[selection_variable]
    i = frame_1.start_class.GetSelection()
    j = frame_1.end_class.GetSelection()
    #frame_1.end_class.
    #selection_variable_values = list(class_selection)
    #selection_variable_values.sort()
    selection_variable_values= class_selection[i:j+1]
    #frame_1.selection_variable_list
    #frame_1.selection_variable_list
    #selection_variable = frame_1.selection_variable.GetValue()
    #selection_variable_range = frame_1.selection_variable.GetValue()
    #selection_variable_values = 
    #print selection_variable_values
    #exit(0)
    


    #jobs = model.start_epistasis(c1,c2,g1,g2,t1,t2,sv,datafile,outputdir,local_mode)
    jobs = model.start_epistasis(genelist=genes,traitlist=traits,selection_variable=selection_variable, selection_variable_values=selection_variable_values,local_mode=local_mode,data=datafile,output_dir=outputdir)
    
    model.epistasis_status=exec_state
    
   
            
def stop():
    model.stop_epistasis()
    model.clean_up_epistasis()
    model.__init__()
    EnableControls(True)
    frame_1.timer.Stop()
    
def post_commands():
    post_exec_str = frame_1.post_exec_cmds.GetValue()
    post_exec_commands = post_exec_str.split(";\n")
    for cmd in post_exec_commands:
        try:
            proc = os.popen(cmd, "w")
            proc.close()
            
        except OSError:
            print "Unable to execute command :"+cmd
            
    
def final():
    model.clean_up_epistasis()
    post_commands()


def EnableControls(enable):
    frame_1.datafile.Enable(enable)
    frame_1.g1.Enable(enable)
    frame_1.g2.Enable(enable)
    frame_1.t1.Enable(enable)
    frame_1.t2.Enable(enable)
    #frame_1.sv.Enable(enable)
    frame_1.datafile.Enable(enable)
    frame_1.outputdir.Enable(enable)
    frame_1.button_1.Enable(enable)
    frame_1.button_2.Enable(enable)
    frame_1.Start.Enable(enable)
    frame_1.runlocal.Enable(enable)
    #frame_1.c1.Enable(enable)
    #frame_1.c2.Enable(enable)

##### BUTTONS ############

# event handlers
def OnBtnStart(event=None):
    model.epistasis_status = pending_state
    frame_1.statusfeed.Clear()
    frame_1.statusfeed.write("Starting epistasis...")
    EnableControls(False)
    TIMER_ID = 100  # pick a number
    shorttime= 100
    frame_1.timer = wx.Timer(frame_1, TIMER_ID)  # message will be sent to the panel
    frame_1.timer.Start(shorttime) 

def OnBtnStop(event=None):
    if model.epistasis_status == exec_state:
        #print "stopping epistasis"
        #model.stopbs(self.epijobs)
            #epiCleanUp(self.epijobs)
            #   self.status="cancelled"
            # else: 
            #   print "Not executing..."
        
        model.epistasis_status = cancelled_state
        shorttime= 100
        frame_1.statusfeed.Clear()
        frame_1.statusfeed.write("Stopping epistasis...")
        frame_1.timer.Start(shorttime) 
     
#frame_1.frame_1_statusbar.SetStatusText("Cancelled epistasis")
    #model.stopEpistasis()
    
def OnBtnBrowseFile(event=None):
    path = os.curdir
    fd = wx.FileDialog(frame_1, message="Choose file")
    fd.ShowModal()
    fd.Destroy()
    frame_1.datafile.Clear()
    frame_1.datafile.write(fd.GetPath())
    read_data_sheet()

def OnBtnBrowseDir(event=None):
    path = frame_1.outputdir.GetValue()
    if path == "":
        path = os.curdir
    dd = wx.DirDialog(frame_1, message="Choose dir",  defaultPath=path)
    dd.ShowModal()
    dd.Destroy()
    frame_1.outputdir.Clear()
    frame_1.outputdir.write(dd.GetPath())


def OnMenuQuit(event=None):
    if model.epistasis_status == exec_state:
        model.stop_epistasis()
    frame_1.Destroy()

def OnTimer(event=None):
    if model.epistasis_status == pending_state:
        start()
    elif model.epistasis_status == exec_state:
        status, progress = model.get_epistasis_status()
        frame_1.statusfeed.Clear()
        frame_1.statusfeed.write(status)
        frame_1.progress.Clear()
        frame_1.progress.write(progress)
    #print "timer event"
        frame_1.timer.Start(timeout)  
    elif model.epistasis_status == finished_state:
        popup_box('Epistasis is complete', 'Epistasis finished')
        frame_1.Stop.Enable(False)
        frame_1.timer.Stop()
        frame_1.button_2.Enable(True)
        frame_1.Destroy()
        final()
    elif model.epistasis_status == cancelled_state:
        stop()
        final()
        #return

#def OnLocal(event=None):
 #   model.localmode = not model.localmode
    #print model.localmode

def on_use_indexes(event=None):
    value = frame_1.use_indexes.GetValue()
    #print value
    
    #frame_1.grid_sizer_2.Enable(value)
    frame_1.gene_index1_label.Enable(value)
    frame_1.gene_index2_label.Enable(value)
    frame_1.trait_index1_label.Enable(value)
    frame_1.trait_index2_label.Enable(value)
    #frame_1.sv_label.Enable(value)
    #frame_1.classes_label.Enable(value)
    
    frame_1.g1.Enable(value)
    frame_1.g2.Enable(value)
    frame_1.t1.Enable(value)
    frame_1.t2.Enable(value)
    #frame_1.sv.Enable(value)
    #frame_1.to_label.Enable(value)
    #frame_1.c1.Enable(value)
    #frame_1.c2.Enable(value)
   
    
def on_choice(event=None):
    sel_var = frame_1.selection_variable_list.GetSelection()
    print sel_var
    #value_list = data_sheet[all_genes_and_traits[sel_var]]
    value_list = data_sheet[sel_var]
    
    values = list(set(value_list))
    
    # all values are either float or string
    if type(values[0]) == float:
         values = filter(lambda x : str(x) not in  ["nan","-99.0"], values)
    elif type(values[0]) == str: 
        values = filter(lambda x : x.strip() not in  ["?"], values)

    #filter(lambda x : x not in  [nan, "?","-99"], values)
    
#    print values 
    values.sort()

#    print values  
    #values = map(lambda y : if(y % 1 == 0.0) : int(y) ,values)
    def clean(v): 
        #print type(v)
        if type(v) == type(1.0) and v % 1 == 0.0:
            v = int(v)
        str_v = str(v).strip()
        #if str_v in ["nan", "?","-99"]:
        #    return
        return str_v

    values = map(clean,values)
    
    #values = filter(lambda x : x not in  ["nan", "?","-99"], values)
    
#    print values  
    #values = set(map(lambda y : str(y).strip(),values))
#values.update()
    
    #values.discard("nan")
    #values.discard("-99")
    #values.discard("?")
    #print values
    #values = list(values)
    #values.sort()
    #print values
    frame_1.start_class.SetItems(values)
    frame_1.start_class.SetSelection(0)
    frame_1.end_class.SetItems(values)
    frame_1.end_class.SetSelection(len(values)-1)
    #class_selection.clear()
    while(class_selection != []):
        class_selection.pop(0)
    class_selection.extend(values)
    
def bindViewerEvents():
    frame_1.button_1.Bind(wx.EVT_BUTTON, OnBtnBrowseFile)
    frame_1.button_2.Bind(wx.EVT_BUTTON, OnBtnBrowseDir)
    frame_1.Start.Bind(wx.EVT_BUTTON, OnBtnStart)
    frame_1.Stop.Bind(wx.EVT_BUTTON, OnBtnStop)
    frame_1.add_genes.Bind(wx.EVT_BUTTON,on_add_genes)
    frame_1.remove_genes.Bind(wx.EVT_BUTTON,  on_remove_genes)
    frame_1.add_traits.Bind(wx.EVT_BUTTON,on_add_traits)
    frame_1.remove_traits.Bind(wx.EVT_BUTTON,  on_remove_traits)
    #frame_1.notebook_1_pane_2.Bind(wx.EVT_BUTTON,on_gene_selector_tab)
    #frame_1.notebook_1_pane_2.Bind(wx.EVT_KEY_DOWN,on_gene_selector_tab)
    frame_1.use_indexes.Bind(wx.EVT_CHECKBOX, on_use_indexes)
    frame_1.selection_variable_list.Bind(wx.EVT_CHOICE,on_choice)
    
    frame_1.Bind(wx.EVT_MENU, OnMenuQuit)
    frame_1.Bind(wx.EVT_TIMER, OnTimer)
   

#    frame_1.runlocal.Bind(wx.EVT_CHECKBOX, OnLocal)
if __name__ == '__main__':
    app = wx.PySimpleApp(0)
    wx.InitAllImageHandlers()
    frame_1 = viewer.MyEpiFrame(None, -1, "")
    timeout = 5000
    model = EpiModel.GridEpistasis()
    #read_genes()
    read_data_sheet()
    app.SetTopWindow(frame_1)
    bindViewerEvents()
    frame_1.Show()
    app.MainLoop()
