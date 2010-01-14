/*
MiG Advanced Shell
Nov, 2009 by Yang Zhao (student@live.cn)
License: GPL v2
This is a subproject affiliated to Minimium Intrusion Grid (MiG) directed by Prof. Brian Vinter.
The purpose is to improve web UI and provide a managerial shortcut for trivial operations.
*/

Shell=function (selfname, pagelayer, serviceurl)
{
    this.selfname=selfname;
    this.serviceurl=serviceurl;
    this.pagelayer=pagelayer;
}
Shell.prototype.CheckBrowser=function ()
{
    if(window.navigator.userAgent.indexOf("MSIE")>=0)
        return 0;
    else if(window.navigator.userAgent.indexOf("Mozilla")>=0)
        return 1;
    else if(window.navigator.userAgent.indexOf("Safari")>=0)
        return 2;
    else if(window.navigator.userAgent.indexOf("Opera")>=0)
        return 3;
    else if(window.navigator.userAgent.indexOf("Chrome")>=0)
        return 4;
    else
        return -1;
}
Shell.prototype.Init=function ()
{
    this.browsertype=this.CheckBrowser();
    this.gui=new Gui(this.selfname+".gui", this.pagelayer, this.browsertype);
    this.ajax=new AjaxService(this.selfname+".ajax", this.browsertype, this.serviceurl);
    this.output=new Output(this.selfname+'.output', this.browsertype);
    this.intellisense=new Intellisense(this.selfname+'.intellisense', this.browsertype);
    this.status=new Status(this.selfname+'.status');
    this.lib=new Lib(this.selfname+".lib", this.browsertype, this.gui, this.ajax, this.output, this.intellisense, this.status);
    this.lib.Init();
    this.Open();
}
Shell.prototype.Open=function ()
{
    this.lib.Open();
}
