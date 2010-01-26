/*
MiG Advanced Shell
Nov, 2009 by Yang Zhao (student@live.cn)
License: GPL v2
This is a subproject affiliated to Minimium Intrusion Grid (MiG) directed by Prof. Brian Vinter.
The purpose is to improve web UI and provide a managerial shortcut for trivial operations.
*/
Lib=function (selfname, gui, ajax, output, intellisense, status)
{
    this.selfname=selfname;
    this.gui=gui;
    this.ajax=ajax;
    this.output=output;
    this.intellisense=intellisense;
    this.status=status;
}
Lib.prototype.Init=function ()
{
    this.gui.Init(this);
    this.ajax.Init();
    this.output.Init(this.gui);
    this.intellisense.Init();
    this.status.Init();
    
    //field identifier for the essential parameter
    this.required='MUST_BE_SET_AND_NO_DEFAULT_VALUE';
    //field identifier for optional parameter flags
    this.flags='flags';
    //priority in command match. Set 1 if to match remote methods first.
    this.priority=1;
    //methods repository
    this.methods=[
  /* Entry Format: [ method names (standard one first), 
                     argument/default list, 
                     0(local) or 1(remote) ]   
     Semantics for an entry: when one of the names is entered on the cmd line,
			1. check arguments, reject if something wrong with arg.s
            2. if local: call a local method "Shell<Name>" where <Name> is
            			the first method names, with first letter capitalized
               if remote: call the method (same name, from registering it
               			with Probe) via XMLRPC
  */
    [['help','man'], "{'method': ['']}", 0],
    [['clear'], "", 0],
    [['list'], "{'type': ['']}", 0],
    [['cd'], "{'path': ['']}", 0],
    [['upload'],"",0],
    [['exit','quit'],"",0]
    ];
    //get all remote methods
    this.methods=this.Probe(this.methods);
    //get current user info
    this.status.user=this.GetUserDN();
}
Lib.prototype.Open=function()
{
    this.gui.Output("Grid - Advanced Shell Interface");
    this.gui.Output(Date());
    this.gui.SetPrompt(this.status.GetPrompt());
}
Lib.prototype.Output=function(obj)
{
    this.gui.Output(ShowObject(obj));
}
Lib.prototype.HookKey=function (e)
{
    var e=e?e:(window.e?window.e:null);
    var code=e.keyCode?e.keyCode:(e.which?e.which:e.charCode);
    switch(code)
    {
        case 13: //Enter
            this.gui.UpdatePrompt();
            this.OnCommand();
            this.gui.PageScroll();
            this.gui.SetCommand('');
            this.gui.FocusInput();
            break;
        case 9: //Tab
        case 38: //Up
        case 40: //Down
            window.event?e.returnValue=false:e.preventDefault();
            var history;
            if(this.status.lastkeycode!=9&&this.status.lastkeycode!=38&&this.status.lastkeycode!=40)
            {
                history=this.intellisense.OnIntellisense(this.gui.GetCommand());
            }
            else
            {
                history=this.intellisense.GetIntellisense(code);
            }
            if(history!=null)
                this.gui.SetCommand(history);
            break;
    }
    this.status.lastkeycode=code;
}
Lib.prototype.OnMouseUp=function()
{
    var userselection;
    if ( window.document.selection ) {
	/* IE style browser */
	userselection = window.document.selection.createRange();
    }
    else if ( window.document.getSelection ) {
	userselection=window.document.getSelection();
    } 
    else return;
    if(userselection!='')
        this.status.clipboard=userselection;
    //this.gui.FocusInput();
}
Lib.prototype.ShellUpload=function()
{
    this.gui.Output(this.gui.CreateUpload(this.status.DirToString(this.status.dir)));
}
Lib.prototype.ShellCd=function(param)
{
    this.Output(param);
    var c=this.ajax.Invoke('ls', [param]);
    if (/\*/.test(param.path[0])) {
        this.gui.Output('cd: Wildcards not supported!');
	return;
    }
    if(c[1][0]!=0)
    {
        this.gui.Output('Directory not found!');
        return;
    }
    else
    {
        this.status.GetDir(param.path[0],true, true);
        this.gui.SetPrompt(this.status.GetPrompt());
	return;
    }
}
Lib.prototype.ShellHelp=function(param)
{
    if(!param.hasOwnProperty('method'))
    {
        this.gui.Output('Advanced Grid Shell    - Help');
        this.gui.Output('list [console|remote]  - to show all/console/remote commands.');
        this.gui.Output('help <command name> - to show help of a certain command.');
        this.gui.Output('Note: this shell does not support pipes or redirection\n');
        this.gui.Output('----------');
    }
    else
    {
        if(this.MethodExist(param.method, this.methods))
            this.gui.Output(this.MethodHelp(this.GetMethod(param.method, this.methods), this.required, this.flags));
        else
            this.gui.Output('Unsupported command or invalid input!');
    }
}
Lib.prototype.ShellClear=function()
{
    this.gui.Clear();
}
Lib.prototype.ShellList=function(param)
{        
    if(!param)param=new Object();
    show=function(methodnames, head, lib)
    {
        lib.gui.Output('----------'+head+'------------');
        for(i in methodnames)
            lib.Output(methodnames[i]);
    }
    if(param.hasOwnProperty('type'))
    {
        var ml=this.ListMethod(this.methods);
        if(param.type=='console')
            show(ml[0], 'Console Methods', this);
        else if(param.type=='remote')
            show(ml[1], 'Remote Methods', this);
        else
            this.ShellList();
    }
    else
    {
        this.ShellList({type: 'console'});
        this.ShellList({type: 'remote'});
    }
}

Lib.prototype.ShellExit=function () {

    window.close();
    // and if we survive it, go to dashboard
    window.location='/';
}

Lib.prototype.GetUserDN=function ()
{
    var str=this.ajax.Invoke('my_id', null);
    var re=new RegExp('/CN=(.[^/]*)');
    var tmp=str.match(re);
    if(tmp[1]=='undefined')
        return 'unknown';
    else
        return tmp[1];
}

Lib.prototype.AddMethod=function(names, signature, islocal, methodlist)
{
    methodlist.push([names, signature, islocal]);
}
Lib.prototype.MethodExist=function(name, methodlist)
{
    for(var i=0;i<methodlist.length;i++)
        for(var j=0;j<methodlist[i][0].length;j++)
            if(name==methodlist[i][0][j])
                return true;
    return;
}
Lib.prototype.GetMethod=function(name, methodlist, priority)
{
    var method=null;
    for(var i=0;i<methodlist.length;i++)
        for(var j=0;j<methodlist[i][0].length;j++)
            if(name==methodlist[i][0][j])
            {
                method=methodlist[i];
                if(method[2]==priority)
                    return method;
            }
    return method;
}
Lib.prototype.ListMethod=function(methodlist)
{
    var list=[[],[]];
    for(i in methodlist)
        list[methodlist[i][2]].push(methodlist[i][0]);
    return list;
}
Lib.prototype.OnCommand=function ()
{
    var command=this.gui.GetCommand();
    this.intellisense.HistoryUpdate(command,10); // number of recorded history commands
    var tokens=SplitCmd(command);
    method=this.GetMethod(tokens[0], this.methods, this.priority);
    if(method)
    {
        this.HandleCommand(tokens, method, this.required, this.flags);
    }else
        this.gui.Output('Invalid Command!');
}
Lib.prototype.HandleCommand=function(tokens, method, required, flags)
{
    var optionalfields=this.GetOptionalFields(method, required, flags);
    var requiredfields=this.GetRequiredFields(method, required);
    var hasflags=this.GetFlags(method, flags);
    params=this.GetOpt(tokens.slice(1), requiredfields, optionalfields, 'abcdefghijklmnopqrstuvwxyz',[],[],'',this.status);
    if(typeof params=='number')
    {
        this.Output('Missing '+params+' arguments!');
        return;
    }
    var param=this.Evaluate(params, method, flags, hasflags);
    if(method[2]==0)
    {
        eval('this.Shell'+method[0][0][0].toUpperCase()+method[0][0].substr(1)+'(param);')
        delete param;
    }
    else if(method[2]==1)
    {
        var arguments=(param===null?null:[param]);
        var r=this.ajax.Invoke(method[0], arguments);
        delete param;
        this.ShowResult(r);
    }
}
Lib.prototype.AddValue=function(array, field, value, status)
{
    if(status.IsPathField(field))
        value=status.DirToString(status.GetDir(value, false, false));
    array.push([field, value]);
}
Lib.prototype.GetOpt=function (tokens, requiredfields, optionalfields, flagstring, args, options, flags, status)
{
    if(tokens.length==0)
    {
        if(requiredfields.length==0)
        {
            for(var i=0;i<optionalfields.length;i++) //the remaining optional fields
            {
                if(optionalfields[i])
                {
                    if(status.IsPathField(optionalfields[i])==true) //if it contains any default path value, combine it with the current dir.
                    {
                        var newpath=status.DirToString(status.GetDir('.', false, false));
                        options.push([optionalfields[i], newpath]);
                        optionalfields[i]=null;
                    }
                }
            }
            if(flags.length>1) //unique value render
            {
                var s1=flags.replace(/(.).*\1/g,"$1");
                var re=new RegExp('['+s1+']','g');
                var s2=flags.replace(re,"");
                flags=s1+s2;
            }
            return [args, options, flags];
        }
        else
            return requiredfields.length;
    }
    /*For required fields*/
    if(tokens[0].match(/^-.*$/)==null)
    {
        if(requiredfields.length>0)
        {
            this.AddValue(args, requiredfields.shift(), tokens[0], status);
        }
        else
        {
            for(var i=0;i<optionalfields.length;i++)
            {
                if(optionalfields[i])
                {
                    this.AddValue(options, optionalfields[i], tokens[0], status);
                    optionalfields[i]=null;
                    break;
                }
            }
        }
        return this.GetOpt(tokens.slice(1), requiredfields, optionalfields, flagstring, args, options, flags, status);
    }
    /*For optional fields*/
    for(var i=0;i<optionalfields.length;i++)
    {
        if(optionalfields[i])
        {
            //support partial matching on option's name
            var re=new RegExp('^'+tokens[0].substr(1));
            var x=optionalfields[i].match(re);
            if(x!=null)
            {
                if(tokens[1]&&tokens[1].match(/^-.*/)==null)
                    this.AddValue(options, optionalfields[i], tokens[1], status);
                else
                    this.AddValue(options, optionalfields[i], '', status);
                optionalfields[i]=null;
                return this.GetOpt(tokens.slice(2), requiredfields, optionalfields, flagstring, args, options, flags, status);
            }
        }
    }
    var re=new RegExp('^-['+flagstring+']+$');
    var o=tokens[0].match(re);
    if(o!=null)
    {
        flags=flags+o[0].substr(1);
        return this.GetOpt(tokens.slice(1), requiredfields, optionalfields, flagstring, args, options, flags, status);
    }
    return this.GetOpt(tokens.slice(1), requiredfields, optionalfields, flagstring, args, options, flags, status);
}

Lib.prototype.GetRequiredFields=function(method, required)
{
    var re=new RegExp("\'[^\']*\'(?=: (?=\'"+required+"\'))",'g');
    var list=method[1].match(re);
    if(list!=null)
    {
        for(var i=0;i<list.length;i++)
            list[i]=list[i].substr(1,list[i].length-2);
        return list;
    }
    else
        return [];
}
Lib.prototype.GetOptionalFields=function (method, required, flags)
{
    var re=new RegExp("\'[^\']*\'(?=: (?!\'"+required+"\'))",'g');
    var list=method[1].match(re);
    var result=[];
    if(list!=null)
        for(var i=0;i<list.length;i++)
            if(list[i].match(flags)==null)
                result.push(list[i].substr(1,list[i].length-2));
    return result;
}
Lib.prototype.GetFlags=function (method, flags)
{
    return method[1].match(flags);
}
Lib.prototype.Evaluate=function(params, method, flags, hasflags)
{
    if(method[1]!='none, array')
    {
        var param=new Object();
        for (i in params[0])
            param[params[0][i][0]]=[params[0][i][1]]; // required param.name=[value]
        for(i in params[1])
            param[params[1][i][0]]=[params[1][i][1]]; // optional param.name=[value]
        if(hasflags)
            param[flags]=params[2]; //flags param.flags=value;
        return param;
    }else
        return null;
}
Lib.prototype.Probe=function (methodlist)
{
    var methods=this.ajax.Invoke("AllMethodSignatures", null);
    for(var i=0;i<methods.length;i++)
        if(methods[i][0].indexOf('system.')<0)
            this.AddMethod([methods[i][0]], methods[i][1], 1, methodlist);
    return methodlist;
}
Lib.prototype.MethodHelp=function(method, required, flags)
{
    var rf=this.GetRequiredFields(method, required);
    var of=this.GetOptionalFields(method, required, flags);
    var fl=this.GetFlags(method, flags);
    var str=method[0]+' Required:['+rf+'] '+' Optional:['+of+'] '+' Flags:['+fl+']';
    return str;
}
Lib.prototype.ShowResult=function(resultobject)
{
    if(resultobject.hasOwnProperty('faultCode')&&resultobject.hasOwnProperty('faultString'))
    {
        this.gui.Output('Internal Error '+resultobject.faultCode+': '+resultobject.faultString);
        this.gui.Output('The type signature of this method may be missed or incorrect.');
    }else
    {
        this.output.Accept(resultobject);
    }
}