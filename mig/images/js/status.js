/*
MiG Advanced Shell
Nov, 2009 by Yang Zhao (student@live.cn)
License: GPL v2
This is a subproject affiliated to Minimium Intrusion Grid (MiG) directed by Prof. Brian Vinter.
The purpose is to improve web UI and provide a managerial shortcut for trivial operations.
*/
Status=function(selfname)
{
    this.selfname=selfname;
    // record the last key for intellisense switch
    this.lastkeycode=-1;
    // remained for use
    this.clipboard='';
    this.dir=['/'];
    this.user='';
    this.pathfields=['path', 'src', 'dst']; // predefined pathfields
}
Status.prototype.Init=function()
{
}
Status.prototype.IsPathField=function(field)
{
    for(var i=0;i<this.pathfields.length;i++)
        if(this.pathfields[i]==field)
            return true;
    return false;
}
//get a copy of current dir array
Status.prototype.CloneDir=function()
{
    var x=[];
    for(var i=0;i<this.dir.length;i++)
        x.push(this.dir[i]);
    return x;
}
//get a prompt string
Status.prototype.GetPrompt=function()
{
    return this.user+'@'+this.DirToString(this.dir)+'>';
}
//get a dir out after pushing in a dir
//path: dir string to put in
//update: true if you want it to has side-effect on the current dir in the status
//absolute(explict): true if it's an absolute path string
Status.prototype.GetDir=function(path, update, absolute)
{
    if(absolute!=true)
        absolute=this.IsAbsolute(path);
    if(update==true)
    {
        if(absolute==true)
        {
            this.dir=this.StringToDir(path);
            this.dir.unshift('/');
            return this.dir;
        }else
            return this.JoinDir(this.dir, this.StringToDir(path));
    }else
    {
        if(absolute==true)
        {
            if(path=='/')
                return ['/'];
            return this.StringToDir(path);
        }else
        {
            return this.JoinDir(this.CloneDir(), this.StringToDir(path));
        }
    }
}
//return string by joinning dir parts
Status.prototype.DirToString=function(dir)
{
    return dir.length>1?dir.join('/').slice(1):dir[0];
}
//return dir by splitting path string
Status.prototype.StringToDir=function(str)
{
    var r= str.split(/[\/]+/);
    if(r[r.length-1]=='')
        r.pop();
    return r;
}
Status.prototype.IsAbsolute=function(path)
{
    if(path[0]=='/')
        return true;
    else
        return false;
}
//the conjunction of dirs
Status.prototype.JoinDir=function(dir, newdir)
{
    if(newdir.length==0)
        return dir;
    var x=newdir[0];
    switch(x)
    {
        case '.':
            newdir.shift();
            return this.JoinDir(dir, newdir);
        case '..':
            if(dir.length>1)
                dir.pop();
            newdir.shift();
            return this.JoinDir(dir, newdir);
        default:
            dir.push(newdir.shift());
            return this.JoinDir(dir, newdir);
    }
}