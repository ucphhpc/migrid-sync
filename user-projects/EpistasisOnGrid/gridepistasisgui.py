
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
all_genes = list()

def popup_box(comment, caption_title=" "):
    dlg = wx.MessageDialog(frame_1,
                           message=comment,
                           caption=caption_title,
                           style=wx.OK|wx.ICON_INFORMATION
                           )
    dlg.ShowModal()
    dlg.Destroy()

######## GENE SELECTOR TAB###########

def read_genes():

    datafile = frame_1.datafile.GetValue()
    if not os.path.exists(datafile):
        popup_box("Can't find "+datafile)
        return
    #print all_genes
    gene_data = readdata.read_data(datafile)
    all_genes.extend(gene_data)
    #all_genes.sort()
    frame_1.gene_list.Set(all_genes)

def on_gene_selector_tab(event=None):
    print "event"
    read_genes()

##### BUTTONS ############                        

def update_selected_genes():
    frame_1.selected_genes.Set(list(gene_selection))

def on_add_genes(event=None):
    index = frame_1.gene_list.GetSelections()
    indexes = list(index)
    print indexes, all_genes
    #frame_1.selected_genes.InsertItems(index, 0)
    for i in indexes: 
#        gene_name = all_genes[i]
        #if not gene_name in gene_selection:
        #gene_selection.append(all_genes[i])
        gene_selection.add(all_genes[i])
    update_selected_genes()
    
def on_remove_genes(event=None):
    indexes = list(frame_1.selected_genes.GetSelections())
    indexes.reverse()
    print indexes
    
    for i in indexes: 
        gene_selection.remove(list(gene_selection)[i])
    #gene_selection.remove(genes)
    update_selected_genes()
 

#### GENERAL TAB ############

def validateInput():
    try: 
        g1 = int(frame_1.g1.GetValue())
        g2 = int(frame_1.g2.GetValue())
        t1 = int(frame_1.t1.GetValue())
        t2 = int(frame_1.t2.GetValue())
        sv = int(frame_1.sv.GetValue())
        c1 = int(frame_1.c1.GetValue())
        c2 = int(frame_1.c2.GetValue()) 
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
    g1 = frame_1.g1.GetValue()
    g2 = frame_1.g2.GetValue()
    t1 = frame_1.t1.GetValue()
    t2 = frame_1.t2.GetValue()
    sv = frame_1.sv.GetValue()
    c1 = frame_1.c1.GetValue()
    c2 = frame_1.c2.GetValue()
    datafile = frame_1.datafile.GetValue()
    outputdir = frame_1.outputdir.GetValue()
    local_mode = frame_1.runlocal.GetValue()

    
    if outputdir[-1] != "/":
        outputdir += "/"

    jobs = model.start_epistasis(c1,c2,g1,g2,t1,t2,sv,datafile,outputdir,local_mode)
    model.epistasis_status=exec_state
    
   
            
def stop():
    model.stop_epistasis()
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
    frame_1.sv.Enable(enable)
    frame_1.datafile.Enable(enable)
    frame_1.outputdir.Enable(enable)
    frame_1.button_1.Enable(enable)
    frame_1.button_2.Enable(enable)
    frame_1.Start.Enable(enable)
    frame_1.runlocal.Enable(enable)
    frame_1.c1.Enable(enable)
    frame_1.c2.Enable(enable)

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
        print "stopping epistasis"
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
    read_genes()

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

def bindViewerEvents():
    frame_1.button_1.Bind(wx.EVT_BUTTON, OnBtnBrowseFile)
    frame_1.button_2.Bind(wx.EVT_BUTTON, OnBtnBrowseDir)
    frame_1.Start.Bind(wx.EVT_BUTTON, OnBtnStart)
    frame_1.Stop.Bind(wx.EVT_BUTTON, OnBtnStop)
    frame_1.add_genes.Bind(wx.EVT_BUTTON,on_add_genes)
    frame_1.remove_genes.Bind(wx.EVT_BUTTON,  on_remove_genes)
    #frame_1.notebook_1_pane_2.Bind(wx.EVT_BUTTON,on_gene_selector_tab)
    frame_1.notebook_1_pane_2.Bind(wx.EVT_KEY_DOWN,on_gene_selector_tab)
    
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
    
    app.SetTopWindow(frame_1)
    bindViewerEvents()
    frame_1.Show()
    app.MainLoop()
