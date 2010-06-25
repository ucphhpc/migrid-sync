/*
MiG Advanced Shell
Nov, 2009 by Yang Zhao (student@live.cn)
License: GPL v2
This is a subproject affiliated to Minimium Intrusion Grid (MiG) directed by Prof. Brian Vinter.
The purpose is to improve web UI and provide a managerial shortcut for trivial operations.
*/
Gui=function (selfname, pagelayer)
{
    this.pagelayer=pagelayer;
    this.selfname=selfname;
}
Gui.prototype.Init=function (lib)
{
    this.lib=lib;
    this.CreateLayer();
    this.SetBehaviour();
    this.FocusInput();
}
Gui.prototype.CreateLayer=function ()
{
    var root=document.getElementById(this.pagelayer);
    
    root.innerHTML+="<iframe name='hidden_iframe' id='hidden_iframe' style='display:none'></iframe>";
    
    var divOutput=document.createElement("div");
    divOutput.setAttribute("id","divShellOutput");
    
    var divInput=document.createElement("div");
    divInput.setAttribute("id","divShellInput");
    
    var formInput=document.createElement("form");
    formInput.setAttribute("id","formShellInput");
    formInput.setAttribute("onsubmit","return false;");
    formInput.setAttribute("action","");

    var divPrompt=document.createElement("div");
    divPrompt.setAttribute("id","divShellPrompt");
    var inputCommand=document.createElement("input");
    inputCommand.setAttribute("id","inputShellCommand");
    inputCommand.setAttribute("class","inputShellCommand");
    inputCommand.setAttribute("type","text");
    inputCommand.setAttribute("value","");
    
    var tableInput=this.CreatePrompt(divPrompt,inputCommand);
    
    formInput.appendChild(tableInput);
    divInput.appendChild(formInput);
    
    root.appendChild(divOutput);
    root.appendChild(divInput);
}
Gui.prototype.CreatePrompt=function (Prompt, Command)
{
    var tableInput=document.createElement("table");
    tableInput.setAttribute("class","tableShellInput");
    
    var tablebodyInput=document.createElement("tbody");
    
    var tableInput_tr1=document.createElement("tr");
    tableInput_tr1.setAttribute("class","trShellInput");
    var tableInput_td1=document.createElement("td");
    tableInput_td1.setAttribute("class","tdShellPrompt");
    var tableInput_td2=document.createElement("td");
    tableInput_td2.setAttribute("class","tdShellCommand");
    
    tableInput_td1.appendChild(Prompt);
    tableInput_td2.appendChild(Command);
    
    tableInput_tr1.appendChild(tableInput_td1);
    tableInput_tr1.appendChild(tableInput_td2);
    tablebodyInput.appendChild(tableInput_tr1);
    tableInput.appendChild(tablebodyInput);
    
    return tableInput;
}
Gui.prototype.SetBehaviour=function ()
{
    var root=document.getElementById(this.pagelayer);
    root.setAttribute("onmouseup",this.lib.selfname+".OnMouseUp();"); //shell.lib.OnMouseUp();
    var inputbox=document.getElementById("inputShellCommand");
    inputbox.setAttribute("onkeydown", this.lib.selfname+".HookKey(event);"); //shell.lib.HookKey(event);
    var hiddenframe=document.getElementById("hidden_iframe");
    hiddenframe.onload = hiddenframe.onreadystatechange = function() 
    {
        if (this.readyState && this.readyState != 'complete') return;
        else {
            var str=document.getElementsByTagName('head');
            //TODO: response to upload
        }
    }
}
Gui.prototype.FocusInput=function ()
{
    document.getElementById("inputShellCommand").focus();
}
Gui.prototype.PageScroll=function ()
{
    window.scrollBy(0,122500);
}
Gui.prototype.SetPrompt=function (text)
{
    document.getElementById("divShellPrompt").innerHTML=text;
}
Gui.prototype.SetCommand=function (text)
{
    document.getElementById("inputShellCommand").value=text;
}
Gui.prototype.GetCommand=function ()
{
    return document.getElementById("inputShellCommand").value;
}
Gui.prototype.Output=function (content)
{
    var o=document.getElementById("divShellOutput");
    var d=document.createElement("div");
    if(Type(content)=="STRING"){
        d.textContent !==undefined ? (d.textContent = content) : (d.innerText = content);
        o.appendChild(d);
    }else{
        d.appendChild(content);
        o.appendChild(d);
    }
}
Gui.prototype.UpdatePrompt=function ()
{
    var prompt=document.createElement("div");
    prompt.innerHTML=document.getElementById("divShellPrompt").innerHTML;
    var text=this.GetCommand();
    var command=document.createElement("div");
    command.setAttribute("class","inputShellCommand");
    command.innerHTML=text;
    this.Output(this.CreatePrompt(prompt,command));
}
Gui.prototype.Clear=function ()
{
    var empty=document.createElement('div');
    empty.setAttribute('id','divShellOutput');
    var root=document.getElementById(this.pagelayer);
    root.replaceChild(empty, document.getElementById('divShellOutput'));    
}
Gui.prototype.CreateTable=function(rows, columns)
{
    var table=document.createElement('table');
    var tbody=document.createElement('tbody');
    for(var i=0;i<rows;i++)
    {
        var tr=document.createElement('tr');
        for(var j=0;j<columns;j++)
        {
            var td=document.createElement('td');
            tr.appendChild(td);
        }
        tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    return table;
}
Gui.prototype.FillTable=function(tableelement, row, column, content)
{
    var td=tableelement.getElementsByTagName('tbody')[0].getElementsByTagName('tr')[row].getElementsByTagName('td')[column];
    if(Type(content)=='STRING') {
	// Mozilla style browser
	td.textContent=content;
	// IE style browser
	td.innerText=content;
    }
    else {
        td.appendChild(content);
    }
}
Gui.prototype.CreateUpload=function(dir)
{
    var o=document.createElement("div");
    var str='';
    str+="<form enctype='multipart/form-data' action='upload.py' method='post' target='hidden_iframe'>";
    str+="<input name='fileupload' size=20 type='file'/>";
    str+="<input name='path' type='hidden' value="+dir+"/>";
    str+="<input type='submit' value='upload'/>";
    str+="</form>";
    o.innerHTML=str;
    return o;
}
