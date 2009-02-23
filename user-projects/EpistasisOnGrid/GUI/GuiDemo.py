import wx

class DemoPanel(wx.Panel):
    """This Panel hold two simple buttons, but doesn't really do anything."""
    def __init__(self, parent, *args, **kwargs):
        """Create the DemoPanel."""
        wx.Panel.__init__(self, parent, *args, **kwargs)
        
        self.parent = parent  # Sometimes one can use inline Comments
        
        NothingBtn = wx.Button(self, label="Do Nothing with a long label")
        NothingBtn.Bind(wx.EVT_BUTTON, self.DoNothing )
        
        MsgBtn = wx.Button(self, label="Send Message")
        MsgBtn.Bind(wx.EVT_BUTTON, self.OnMsgBtn )
        
        Sizer = wx.BoxSizer(wx.HORIZONTAL)#VERTICAL)
        Sizer.Add(NothingBtn, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        Sizer.Add(MsgBtn, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        
        self.SetSizerAndFit(Sizer)
        
    def DoNothing(self, event=None):
        """Do nothing."""
        pass
    
    def OnMsgBtn(self, event=None):
        """Bring up a wx.MessageDialog with a useless message."""
        dlg = wx.MessageDialog(self,
                               message='A completely useless message',
                               caption='A Message Box',
                               style=wx.OK|wx.ICON_INFORMATION
                               )
        dlg.ShowModal()
        dlg.Destroy()
        
class DemoFrame(wx.Frame):
    """Main Frame holding the Panel."""
    def __init__(self, *args, **kwargs):
        """Create the DemoFrame."""
        wx.Frame.__init__(self, *args, **kwargs)
        
         # Build the menu bar
        MenuBar = wx.MenuBar()
        
        FileMenu = wx.Menu()
        
        item = FileMenu.Append(wx.ID_EXIT, text="&Quit")
        self.Bind(wx.EVT_MENU, self.OnQuit, item)
        
        MenuBar.Append(FileMenu, "&File")
        self.SetMenuBar(MenuBar)
        
         # Add the Widget Panel
        self.Panel = DemoPanel(self)
        
        self.Fit()
        
    def OnQuit(self, event=None):
        """Exit application."""
        self.Close()
        
if __name__ == '__main__':
    app = wx.App()
    frame = DemoFrame(None, title="Micro App")
    frame.Show()
    app.MainLoop()
    
