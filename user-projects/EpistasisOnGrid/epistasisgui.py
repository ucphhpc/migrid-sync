
import sys
sys.path.append("GUI/")
import  epistasisviewer as viewer
import gridepistasis as EpiModel
import wx
import time
import os

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
    
def start():

    valid, comment = validateInput()
    if not valid: 
        dlg = wx.MessageDialog(frame_1,
                               message=comment,
                               caption='Incorrect input',
                               style=wx.OK|wx.ICON_INFORMATION
                               )
        dlg.ShowModal()
        dlg.Destroy()
        return


#    frame_1.statusfeed.Enable(True)
 
    #frame_1.frame_1_statusbar.SetStatusText("Executing epistasis")
    #frame_1.Show()
    #frame_1.Update()
#time.sleep(5)
    
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

        
   # model = EpiModel.EpistasisProcess()
    #timeout = 5000
    jobs = model.start_epistasis(c1,c2,g1,g2,t1,t2,sv,datafile,outputdir,local_mode)
    model.epistasis_status="executing"
    # fake response
    #dlg = wx.MessageDialog(frame_1,
    #                           message='Executing epistasis',
    #                           caption='Start epistasis',
    #                           style=wx.OK|wx.ICON_INFORMATION
    #                           )
   # dlg.ShowModal()
    #dlg.Destroy()
    # set an update timer
  # x100 milliseconds

def stop():
    model.stop_epistasis()
    model.__init__()
    EnableControls(True)

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

# event handlers
def OnBtnStart(event=None):
    model.epistasis_status = "pending"
    frame_1.statusfeed.Clear()
    frame_1.statusfeed.write("Starting epistasis...")
    EnableControls(False)
    TIMER_ID = 100  # pick a number
    shorttime= 100
    frame_1.timer = wx.Timer(frame_1, TIMER_ID)  # message will be sent to the panel
    frame_1.timer.Start(shorttime) 

def OnBtnStop(event=None):
    if model.epistasis_status == "executing":
        print "stopping epistasis"
        #model.stopbs(self.epijobs)
            #epiCleanUp(self.epijobs)
            #   self.status="cancelled"
            # else: 
            #   print "Not executing..."
        
        model.epistasis_status = "stopping"
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
    if model.epistasis_status == "executing":
        model.stop_epistasis()
    frame_1.Destroy()

def OnTimer(event=None):
    if model.epistasis_status == "pending":
        start()
        return
    if model.epistasis_status == "stopping":
        stop()
    #return
    
    status, progress = model.get_epistasis_status()
    frame_1.statusfeed.Clear()
    frame_1.statusfeed.write(status)
    frame_1.progress.Clear()
    frame_1.progress.write(progress)
    #print "timer event"
   
    if model.epistasis_status == "finished":
        #frame_1.button_2.Label("Go to output")
        dlg = wx.MessageDialog(frame_1,
                               message='Epistasis is complete',
                               caption='Epistasis finished',
                               style=wx.OK|wx.ICON_INFORMATION
                               )
        dlg.ShowModal()
        dlg.Destroy()
        frame_1.Stop.Enable(False)
        frame_1.timer.Stop()
        frame_1.button_2.Enable(True)
        frame_1.Destroy()
    else: 
        frame_1.timer.Start(timeout)  

def OnLocal(event=None):
    model.localmode = not model.localmode
    #print model.localmode

def bindViewerEvents():
    frame_1.button_1.Bind(wx.EVT_BUTTON, OnBtnBrowseFile)
    frame_1.button_2.Bind(wx.EVT_BUTTON, OnBtnBrowseDir)
    frame_1.Start.Bind(wx.EVT_BUTTON, OnBtnStart)
    frame_1.Stop.Bind(wx.EVT_BUTTON, OnBtnStop)
    frame_1.Bind(wx.EVT_MENU, OnMenuQuit)
    frame_1.Bind(wx.EVT_TIMER, OnTimer)
    frame_1.runlocal.Bind(wx.EVT_CHECKBOX, OnLocal)
    
app = wx.PySimpleApp(0)
wx.InitAllImageHandlers()
frame_1 = viewer.MyEpiFrame(None, -1, "")
timeout = 5000
model = EpiModel.GridEpistasis()
app.SetTopWindow(frame_1)
bindViewerEvents()
frame_1.Show()
app.MainLoop()
