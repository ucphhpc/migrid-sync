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

Shell.prototype.Init=function ()
{
    this.gui=new Gui(this.selfname+".gui", this.pagelayer);
    this.ajax=new AjaxService(this.selfname+".ajax", this.serviceurl);
    this.output=new Output(this.selfname+'.output');
    this.intellisense=new Intellisense(this.selfname+'.intellisense');
    this.status=new Status(this.selfname+'.status');
    this.lib=new Lib(this.selfname+".lib", this.gui, this.ajax, 
	             this.output, this.intellisense, this.status);
    this.lib.Init();
    this.Open();
}
Shell.prototype.Open=function ()
{
    this.lib.Open();
}
