/*
MiG Advanced Shell
Nov, 2009 by Yang Zhao (student@live.cn)
License: GPL v2
This is a subproject affiliated to Minimium Intrusion Grid (MiG) directed by Prof. Brian Vinter.
The purpose is to improve web UI and provide a managerial shortcut for trivial operations.
*/
Intellisense=function(selfname, browsertype)
{
    this.selfname=selfname;
    this.browsertype=browsertype;
}
Intellisense.prototype.Init=function()
{
    //to store recent executed commands
    this.history=[];
    //a scrolling scope of history
    this.scroll=[];
    //pointer to the scroll
    this.scrollindex=-1;
}

Intellisense.prototype.HistoryUpdate=function(str, histlen)
{
    if(str.match(/^\s*$/)==null)
    {
        this.history.push(str);
        if(this.history.length>histlen)
            this.history.shift();
    }
}
Intellisense.prototype.OnIntellisense=function(str)
{
    this.scroll=[];
    this.scrollindex=-1;
    var re=new RegExp('^'+str);
    var TextInArray=function(str,a)
    {
        for(var i=0;i<a.length;i++)
        if(str==a[i])
            return true;
        return false;
    }
    for(var i=0;i<this.history.length;i++)
    {
        var r;
        r=this.history[i].match(re);
        if(r!=null&&TextInArray(this.history[i],this.scroll)==false)
            this.scroll.push(this.history[i]);
    }
    return this.GetIntellisense(9);
}
Intellisense.prototype.GetIntellisense=function(code)
{
    if(this.scroll.length==0)
        return null;
    if(code==9||code==40)
    {
        this.scrollindex++;
        if(this.scrollindex>this.scroll.length-1)
            this.scrollindex=0;
        return this.scroll[this.scrollindex];
    }else if(code==38)
    {
        this.scrollindex=this.scrollindex-1;
        if(this.scrollindex<0)
            this.scrollindex=this.scroll.length-1;
        return this.scroll[this.scrollindex];
    }
    return null;
}
