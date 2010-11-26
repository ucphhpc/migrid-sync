import sys
sys.path.append("GUI/")
import epistasisviewer as viewer
import gridepistasis as epistasisControl
import wx
#import time
import os
sys.path.append("RfilesAndscripts/")
import readdata
from threading import Thread
import Configuration.epistasisconfiguration as config




exec_state = "executing"
pending_state = "pending"
finished_state = "finished"
cancelled_state = "cancelled"


class gridepistasisgui:
    def __init__(self):
        self.gene_selection = set()
        self.gene_selection_dict = {}
        self.trait_selection = set()
        self.trait_selection_dict = {}
        self.class_selection = list()
        self.all_genes_and_traits = list()
        self.data_sheet = []
        self.jobs = []
        self.epistasis_status = pending_state
        self.epistasis_thread = Thread()
        

    def popup_box(self,comment, caption_title=" "):
        dlg = wx.MessageDialog(frame_1,
                               message=comment,
                               caption=caption_title,
                               style=wx.OK|wx.ICON_INFORMATION
                               )
        dlg.ShowModal()
        dlg.Destroy()

    
    def yesno_box(self,comment, caption_title=" "):
        dlg = wx.MessageDialog(frame_1,
                               message=comment,
                               caption=caption_title,
                               style=wx.YES_DEFAULT|wx.ICON_INFORMATION
                               )
        choice = dlg.ShowModal()
        print choice
        dlg.Destroy()
    
    
    #def load_selection_var_list(self, selection_variables):
        #sel_var = frame_1.selection_variable_list.GetSelection()
        #value_list = self.data_sheet[sel_var]
        #values = list(set(value_list))
        ## all values are either float or string
        #if type(values[0]) == float:
             #values = filter(lambda x : str(x) not in  ["nan","-99.0"], values)
        #elif type(values[0]) == str: 
            #values = filter(lambda x : x.strip() not in  ["?"], values)
        #values.sort()
 
        #def clean(v): 
            #if type(v) == type(1.0) and v % 1 == 0.0:
                #v = int(v)
            #str_v = str(v).strip()
            #return str_v
    
        #values = map(clean,values)
   
        #frame_1.start_class.SetItems(values)
        #frame_1.start_class.SetSelection(0)
        #frame_1.end_class.SetItems(values)
        #frame_1.end_class.SetSelection(len(values)-1)
        #while(self.class_selection != []):
            #self.class_selection.pop(0)
        #self.class_selection.extend(values)
    
    ############################
    ######## GENE SELECTOR TAB###########
    #############################
    def read_data_sheet(self):
        datafile = frame_1.datafile.GetValue()
        if not os.path.exists(datafile):
            self.popup_box("Can't find "+datafile, "Can't find "+datafile)
            return
        #print all_genes_and_traits
        #data_sheet.update(readdata.read_data(datafile))
        data_list, column_labels = readdata.read_data(datafile)
        self.data_sheet.extend(data_list)
        #column_labels = data_sheet.keys()
        self.all_genes_and_traits.extend(column_labels)
        #print "all", all_genes_and_traits
        #all_genes_and_traits.sort()
        frame_1.gene_list.Set(self.all_genes_and_traits)
        frame_1.trait_list.Set(self.all_genes_and_traits)
        # assume that the selection variable is in first columns 
        frame_1.selection_variable_list.SetItems(self.all_genes_and_traits[0:20]) 
        
        
        #frame_1.selection_variable_list.Select(1)
    ##### BUTTONS ############                        
    
    def update_selected_genes(self):
        frame_1.selected_genes.Set(list(self.gene_selection))
    
    def on_add_genes(self,event=None):
        indexes = frame_1.gene_list.GetSelections()
        #indexes = list(index)
        #print indexes, all_genes_and_traits
        #frame_1.selected_genes.InsertItems(index, 0)
        for i in indexes: 
    #        gene_name = all_genes_and_traits[i]
            #if not gene_name in gene_selection:
            #gene_selection.append(all_genes_and_traits[i])
            gene_name = self.all_genes_and_traits[i]
            self.gene_selection.add(gene_name)
            if not self.gene_selection_dict.has_key(gene_name):
                self.gene_selection_dict[gene_name] = i
        self.update_selected_genes()
        
    def on_remove_genes(self,event=None):
        indexes = list(frame_1.selected_genes.GetSelections())
        indexes.reverse()
        #print indexes
        
        for i in indexes: 
            gene_name = list(self.gene_selection)[i] # list converts from set to list
            self.gene_selection.remove(gene_name)
            del(self.gene_selection_dict[gene_name])
        #gene_selection.remove(genes)
        self.update_selected_genes()
     
    ###########################
    ######## TRAIT SELECTOR TAB###########
    ##########################
    
    
    ##### BUTTONS ############                        
    
    def update_selected_traits(self):
        frame_1.selected_traits.Set(list(self.trait_selection))
    
    def on_add_traits(self,event=None):
        indexes = frame_1.trait_list.GetSelections()
        #indexes = list(index)
        
        #frame_1.selected_genes.InsertItems(index, 0)
        for i in indexes: 
            trait_name = self.all_genes_and_traits[i]
            #if not gene_name in gene_selection:
            #gene_selection.append(all_genes_and_traits[i])
            self.trait_selection.add(trait_name)
            if not self.trait_selection_dict.has_key(trait_name):
                self.trait_selection_dict[trait_name] = i
                
        self.update_selected_traits()
        
    def on_remove_traits(self,event=None):
        indexes = list(frame_1.selected_traits.GetSelections())
        indexes.reverse()
        
        
        for i in indexes: 
            trait_name = list(self.trait_selection)[i] # list converts set 
            self.trait_selection.remove(trait_name)
            del(self.trait_selection_dict[trait_name])
        #gene_selection.remove(genes)
        self.update_selected_traits()
    
    ##########################
    #### GENERAL TAB ############
    #########################
    
    def validateInput(self):
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
       
        if frame_1.selection_variable_list.GetSelection() == -1:
            return False, "Choose a selection variable."
    
    
        return True, "OK"
        
    ##### START/ STOP #############
    
    def start(self):

        #collect values
        datafile = frame_1.datafile.GetValue()
        outputdir = frame_1.outputdir.GetValue()
        local_mode = frame_1.runlocal.GetValue()
        print local_mode
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
            genes = self.gene_selection_dict.values()
            traits = self.trait_selection_dict.values()
    
        list_pos = frame_1.selection_variable_list.GetSelection()+1 # indexes start at 1 in R
        selection_variable = list_pos
        i = frame_1.start_class.GetSelection()
        j = frame_1.end_class.GetSelection()
        selection_variable_values= self.class_selection[i:j+1]
                                              
        self.epistasis_thread = My_epistasis_thread(genelist=genes, traitlist=traits, selection_variable=selection_variable, selection_variable_values=selection_variable_values, data=datafile, output_dir=outputdir, local_mode=local_mode)
                                    # genelist,traitlist,selection_variable, selection_variable_values,local_mode,data,output_dir
        frame_1.statusfeed.write("Creating %i jobs..." % len(selection_variable_values))
        self.epistasis_thread.start()
        #jobs = model.start_epistasis(c1,c2,g1,g2,t1,t2,sv,datafile,outputdir,local_mode)
        #self.jobs = self.epistasis_thread.start_epistasis(genelist=genes,traitlist=traits,selection_variable=selection_variable, selection_variable_values=selection_variable_values,local_mode=local_mode,data=datafile,output_dir=outputdir)
        
        #model.epistasis_status=exec_state
        self.epistasis_status = exec_state
        frame_1.timer.Start(milliseconds=2000)  # start the timer for 2 sec
                
    def stop(self):
        self.epistasis_thread.stop()
        #model.clean_up_epistasis()
        #model.__init__()
        self.EnableControls(True)
        #frame_1.timer.Stop()
        #self.update_gui()
        #self.epistasis_thread.join()

    def finish(self):
        self.epistasis_thread.join()
        
        
    def post_commands(self):
        post_exec_str = frame_1.post_exec_cmds.GetValue()
        post_exec_commands = post_exec_str.split(";\n")
        for cmd in post_exec_commands:
            try:
                proc = os.popen(cmd, "w")
                proc.close()
                
            except OSError:
                print "Unable to execute command :"+cmd
                
        
    def final(self):
        #model.clean_up_epistasis()
        self.post_commands()
    
    
    def EnableControls(self,enable):
        frame_1.datafile.Enable(enable)
        #frame_1.g1.Enable(enable)
        #frame_1.g2.Enable(enable)
        #frame_1.t1.Enable(enable)
        #frame_1.t2.Enable(enable)
        #frame_1.sv.Enable(enable)
        frame_1.datafile.Enable(enable)
        frame_1.outputdir.Enable(enable)
        frame_1.button_1.Enable(enable)
        frame_1.button_2.Enable(enable)
        frame_1.Start.Enable(enable)
        frame_1.Stop.Enable(enable)
        frame_1.runlocal.Enable(enable)
        frame_1.use_indexes.Enable(enable)
        #frame_1.c1.Enable(enable)
        #frame_1.c2.Enable(enable)
    
    
    
    def update_gui(self):
    
        if self.epistasis_status == pending_state: # if the grid jobs havent been started, do nothing
            return

        running_jobs = self.epistasis_thread.jobs
        
        finished_jobs = self.epistasis_thread.finished_jobs
        
        all_jobs = []
        all_jobs.extend(running_jobs)
        all_jobs.extend(finished_jobs)
        
        if all_jobs == []: # jobs not ready yet
            return
            
        if len(all_jobs) > 0 and len(all_jobs) == len(finished_jobs) : 
            self.epistasis_status = finished_state
        
        progress_str = str(len(finished_jobs)) + '/'\
             + str(len(all_jobs))
        status_lines = self.create_gui_job_text(all_jobs)
        status = ""
        for line in status_lines:
            status += line + '\n'
        
        frame_1.statusfeed.Clear()
        frame_1.statusfeed.write(status)
        frame_1.progress.Clear()
        frame_1.progress.write(progress_str)
        
    def create_gui_job_text(self,jobs):
        """Return a status string for each job"""
        lines = []
        for j in jobs:
            line = 'Grid Epistasis Job \t %(class)s \t %(status)s \t %(started)s' % j
            lines.append(line)
        return lines
         
  
    ##### BUTTONS ############
    
    # event handlers
    def OnBtnStart(self,event=None):
        valid, comment = self.validateInput()
        if not valid: 
            self.popup_box(comment, "Incorret input")
            return
    
        #model.epistasis_status = pending_state
        self.epistasis_status = pending_state
        frame_1.statusfeed.Clear()
        frame_1.statusfeed.write("Starting epistasis...")
        self.EnableControls(False)
        frame_1.Stop.Enable(True)       
        TIMER_ID = 100  # pick a number
        shorttime= 100
        frame_1.timer = wx.Timer(frame_1, TIMER_ID)  # message will be sent to the panel
        frame_1.timer.Start(shorttime) 
    
    def OnBtnStop(self,event=None):
        if self.epistasis_status == exec_state:
            self.epistasis_status = cancelled_state
            frame_1.statusfeed.Clear()
            frame_1.statusfeed.write("Stopping epistasis...")
            
        
    def OnBtnBrowseFile(self,event=None):
        path = os.curdir
        fd = wx.FileDialog(frame_1, message="Choose file")
        fd.ShowModal()
        fd.Destroy()
        frame_1.datafile.Clear()
        frame_1.datafile.write(fd.GetPath())
        #self.read_data_sheet()
    
    def on_load_button(self, event=None):
        self.read_data_sheet()
        frame_1.statusfeed.Clear()
        frame_1.statusfeed.write("File loaded.")
        epi_gui.EnableControls(True)
        
    
    def OnBtnBrowseDir(self,event=None):
        path = frame_1.outputdir.GetValue()
        if path == "":
            path = os.curdir
        dd = wx.DirDialog(frame_1, message="Choose dir",  defaultPath=path)
        dd.ShowModal()
        dd.Destroy()
        frame_1.outputdir.Clear()
        frame_1.outputdir.write(dd.GetPath())
    
    
    def OnMenuQuit(self,event=None):
        
        if self.epistasis_thread.is_alive():
            self.epistasis_thread.stop()
            self.epistasis_thread.join()
        
        frame_1.Destroy()
    
    
    def on_use_indexes(self,event=None):
        value = frame_1.use_indexes.GetValue()
        frame_1.gene_index1_label.Enable(value)
        frame_1.gene_index2_label.Enable(value)
        frame_1.trait_index1_label.Enable(value)
        frame_1.trait_index2_label.Enable(value)
        frame_1.g1.Enable(value)
        frame_1.g2.Enable(value)
        frame_1.t1.Enable(value)
        frame_1.t2.Enable(value)

    def on_choice(self,event=None):
        sel_var = frame_1.selection_variable_list.GetSelection()
        value_list = self.data_sheet[sel_var]
        values = list(set(value_list))
        # all values are either float or string
        if type(values[0]) == float:
             values = filter(lambda x : str(x) not in  ["nan","-99.0"], values)
        elif type(values[0]) == str: 
            values = filter(lambda x : x.strip() not in  ["?"], values)
        values.sort()
 
        def clean(v): 
            if type(v) == type(1.0) and v % 1 == 0.0:
                v = int(v)
            str_v = str(v).strip()
            return str_v
    
        values = map(clean,values)
   
        frame_1.start_class.SetItems(values)
        frame_1.start_class.SetSelection(0)
        frame_1.end_class.SetItems(values)
        frame_1.end_class.SetSelection(len(values)-1)
        while(self.class_selection != []):
            self.class_selection.pop(0)
        self.class_selection.extend(values)
        
    def bindViewerEvents(self):
        frame_1.button_1.Bind(wx.EVT_BUTTON, self.OnBtnBrowseFile)
        frame_1.load_data_button.Bind(wx.EVT_BUTTON, self.on_load_button)
        frame_1.button_2.Bind(wx.EVT_BUTTON, self.OnBtnBrowseDir)
        frame_1.Start.Bind(wx.EVT_BUTTON, self.OnBtnStart)
        frame_1.Stop.Bind(wx.EVT_BUTTON, self.OnBtnStop)
        frame_1.add_genes.Bind(wx.EVT_BUTTON,self.on_add_genes)
        frame_1.remove_genes.Bind(wx.EVT_BUTTON,  self.on_remove_genes)
        frame_1.add_traits.Bind(wx.EVT_BUTTON,self.on_add_traits)
        frame_1.remove_traits.Bind(wx.EVT_BUTTON,  self.on_remove_traits)
        #frame_1.notebook_1_pane_2.Bind(wx.EVT_BUTTON,on_gene_selector_tab)
        #frame_1.notebook_1_pane_2.Bind(wx.EVT_KEY_DOWN,on_gene_selector_tab)
        frame_1.use_indexes.Bind(wx.EVT_CHECKBOX, self.on_use_indexes)
        frame_1.selection_variable_list.Bind(wx.EVT_CHOICE,self.on_choice)
        
        frame_1.Bind(wx.EVT_MENU, self.OnMenuQuit)
        frame_1.Bind(wx.EVT_CLOSE, self.OnMenuQuit)
        
        frame_1.Bind(wx.EVT_TIMER, self.OnTimer)
    

    def OnTimer(self,event=None):
        #print "timer event. status "+self.epistasis_status, exec_state, self.epistasis_status == exec_state
        self.update_gui()
        #print "restarting timer"
        frame_1.timer.Start(milliseconds=config.gui_update_timer)
            
        if self.epistasis_status == pending_state:
            self.start()
            
        #elif self.epistasis_status == exec_state:
            #print "restarting timer"
            #frame_1.timer.Start(milliseconds=config.gui_update_timer)
            
        elif self.epistasis_status == finished_state:
            frame_1.timer.Stop()
            self.finish()        
            self.popup_box('Result files are in your output directory.', 'Epistasis complete')
            self.final()
            self.EnableControls(True)
                        
        elif self.epistasis_status == cancelled_state:
            self.stop()
            frame_1.timer.Stop()
            self.final()
            self.update_gui()
        

class My_epistasis_thread(Thread):
    
    
    def __init__(self, genelist, traitlist, selection_variable, selection_variable_values, data, output_dir, local_mode):
        Thread.__init__(self)
        self.genelist = genelist
        self.traitlist = traitlist
        self.selection_variable = selection_variable
        self.selection_variable_values = selection_variable_values
        self.data = data
        self.output_dir = output_dir
        self.status = ""
        self.progress = ""
        self.cancel_jobs = False
        self.jobs = []
        self.finished_jobs = []
        self.local_mode = local_mode
        
    def run(self):
        import time
        self.jobs = epistasisControl.start_epistasis(self.selection_variable_values, self.genelist,self.traitlist, self.selection_variable, self.data, self.output_dir, local_mode=self.local_mode)
        total_jobs = len(self.jobs)
        
        time.sleep(5)
        while True:
            print "Updating"
            self.jobs = epistasisControl.update_epistasis(self.jobs)
            
            for j in self.jobs:
                if j["status"] == "FINISHED":
                    epistasisControl.download_output(j)
                    self.jobs.remove(j)
                    self.finished_jobs.append(j)
            if self.cancel_jobs: # Stop
                epistasisControl.stop_epistasis(self.jobs)
                self.jobs = epistasisControl.update_epistasis(self.jobs)
                #self.update_epistasis()
                break
            
            if total_jobs == len(self.finished_jobs): # we're finished
                break
            
            time.sleep(config.polling_update_timer)
            
        print "Thread exiting"
        
    def stop(self):
        self.cancel_jobs = True


#    frame_1.runlocal.Bind(wx.EVT_CHECKBOX, OnLocal)
if __name__ == '__main__':
    epi_gui  = gridepistasisgui()
    
    app = wx.PySimpleApp(0)
    wx.InitAllImageHandlers()
    frame_1 = viewer.MyEpiFrame(None, -1, "")
    # dissable all controls except file browser
    epi_gui.EnableControls(False)
    frame_1.datafile.Enable(True)
    frame_1.button_1.Enable(True)
    frame_1.statusfeed.Clear()
    frame_1.statusfeed.write("Load a data file to get started.")
    #model = EpiModel.GridEpistasis()
    #read_genes()
    #epi_gui.read_data_sheet()
    app.SetTopWindow(frame_1)
    epi_gui.bindViewerEvents()
    frame_1.Show()
    app.MainLoop()
